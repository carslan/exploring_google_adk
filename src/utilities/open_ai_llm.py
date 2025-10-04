# my_openai_llm.py
import json
import re
import uuid
from typing import AsyncGenerator, Any, Optional, Literal, Union

from google.adk.models import LlmResponse, BaseLlm, LlmRequest
# --- ADK types & base LLM ---
from google.genai import types  # ADK uses google.genai Content/Part types
from google.genai.types import Part, Content, FunctionDeclaration
# --- OpenAI async client (v1) ---
from openai import AsyncOpenAI
from openai.types.responses import Response
from pydantic import BaseModel, Field

# --------- Minimal OpenAI-backed LLM for ADK ---------
key = "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"


class SuggestedParameter(BaseModel):
    value: Any = Field(description="Actual and clear value of the parameter")
    tool: str = Field(description="Name of the tool might be invoked")
    param: str = Field(description="Source parameter of the value in the tool response")
    note: Optional[str] = Field(None, description="Explanation of how to extract the value in case requires special logic")


class BaseLlmToolCall(BaseModel):
    tool_name: str = Field(description="Name of the tool must be invoked")
    args: Union[dict[str, Any], dict[str, SuggestedParameter]] = Field(description="Arguments passed to the tool")
    reasoning: str = Field(description="Reasoning of why LLM model picked the tool")  # feature to add maybe, depending on evaluation of aget/tool response


class BaseLlmStructuredOutput(BaseModel):
    type: Literal["tool_call", "content"] = Field(description="Type of the response. 'tool_call' if the given output is to invoke tools. otherwise 'content'.'")
    content: Optional[Any] = Field(None, description="If the type is 'content' then the response of the LLM model.")
    tool_calls: list[BaseLlmToolCall] = Field(description="List of the tools agent must invoke", default_factory=list)
    suggested_tool_calls: list[BaseLlmToolCall] = Field(description="List of suggested tools agent may invoke in after tool invocations", default_factory=list)

    def is_tool_call(self) -> bool:
        return self.type == "tool_call" and self.tool_calls

    def to_tool_calls(self) -> list[Part]:
        tool_calls = []
        for tool_call in self.tool_calls:
            function_call = types.Part.from_function_call(name=tool_call.tool_name, args=tool_call.args)
            function_call.function_call.id = str(uuid.uuid4())
            tool_calls.append(function_call)

        return tool_calls

    def selected_tool_reasoning(self) -> dict:
        return {tool.tool_name: tool.reasoning for tool in self.tool_calls}


class MyOpenAiLlm(BaseLlm):
    """
    Minimal OpenAI wrapper for Google ADK.
    Implements generate_content_async -> yields LlmResponse chunks (streaming or single-shot).
    Tool/function calling intentionally omitted for clarity.
    """
    model: str = "gpt-5-mini"

    async def generate_content_async(
            self,
            request: LlmRequest,
            stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        """
        Core ADK entrypoint.
        - request.system_instruction: types.Content | None
        - request.dynamic_instruction: types.Content | None
        - request.history: list[types.Content]
        - request.new_message: types.Content | None
        - stream: whether ADK expects streaming deltas
        """

        llm_response = await self._send_request(request)

        if llm_response.is_tool_call():
            yield LlmResponse(
                custom_metadata={
                    "selected_tool_reasoning": llm_response.selected_tool_reasoning(),  # must be always JSON serializable.
                    "suggested_tool_calls": llm_response.suggested_tool_calls,
                },
                content=Content(role="assistant", parts=llm_response.to_tool_calls())
            )
        else:
            yield LlmResponse(
                content=types.Content(
                    role="assistant",
                    parts=[Part.from_text(text=llm_response.content)]
                )
            )

    async def _send_request(self, request: LlmRequest) -> BaseLlmStructuredOutput:
        document = ""
        for agent_name, tool in request.tools_dict.items():
            document += f"# Tool {tool.name}\n"
            document += tool.description
            document += "\n\n"

        question = f"""You are a helper agent for an orchestrator to help make a decision whether;
        1- to make tool calls
        2- or, direct possible or helpful answer (if it is not tool calls)

        Below is the documentation for available tools. if the following message(s) requires you to have tool selection(s), then to generate 'tool calls', must use the list below; 
        # Tools:
        {document}

        # Rules:
        - **NEVER** use the samples or examples in the document as a parameter.
        - **ALWAYS** respect the nature of parameters.
        - You must only provide tools have available parameters.
            - You must not include tools by referencing the source parameters from another tool.
            - Value of the parameters must be clearly and actually provided (after required extraction if needed)

        # Expected Output:
        ```json
        {{
            "type": "tool_call (if response is a tool call) | content (if response is not a tool call)"
            "content": $any - if response is not a tool call
            "tool_calls": [
                {{
                    "tool_name": $tool_name,
                    "args": {{ "$required_parameter": $value }}
                    "reasoning": "explain the reason of this tool selection with parameters"
                }}
            ],
            "suggested_tool_calls": [
                {{
                    "tool_name": $suggested_tool_name,
                    "args": {{ 
                        "$tool_parameter": {{
                            "value": $value,
                            "tool": $tool_name - the tool will provide the value for the parameter.
                            "param": $tool_attribute - the source attribute of the value from the source tool.
                            "note": $extraction_note - in case the value requires a special logic to extract.
                        }}
                     }}
                    "reasoning": "explain the reason of this tool suggestion and how to utilize"
                }}
            ]
        }}
        ```
        **DO-NOT provide any additional comment or suggestions. 
        **ALWAYS** respect the given JSON structure.
        """
        desired_query = [{"role": "system", "content": question}]

        for content in request.contents:
            for part in content.parts:
                if part.function_call:
                    tool_call = {
                        "action": "tool_call",
                        "tool": part.function_call.name,
                        "args": part.function_call.args,
                        "tool_call_id": part.function_call.id
                    }
                    desired_query.append({"role": content.role, "content": self.__to_json(tool_call)})
                elif part.function_response:
                    function_declaration: FunctionDeclaration = request.tools_dict[part.function_response.name].function_declaration
                    response_schema = function_declaration.response_json_schema

                    normalized_response = []
                    tool_response = part.function_response.response["result"]
                    if isinstance(tool_response, list):
                        for response in tool_response:
                            normalized_response.append(response_schema(**response).model_dump())
                    else:
                        normalized_response.append(response_schema(**tool_response).model_dump())

                    tool_response = {
                        "action": "tool_call_response",
                        "tool_call_id": part.function_response.id,
                        "output": normalized_response
                    }
                    desired_query.append({"role": content.role, "content": self.__to_json(tool_response)})
                else:
                    desired_query.append({"role": content.role, "content": part.text})

        client = AsyncOpenAI(**{"api_key": key})
        response: Response = await client.responses.create(
            model="gpt-5-mini",
            input=desired_query
        )

        output = response.output_text[0] if isinstance(response.output_text, list) else response.output_text
        filtered_output = re.search(r"\{.*}", output, re.DOTALL)
        return BaseLlmStructuredOutput(**json.loads(filtered_output.group(0))) if filtered_output else BaseLlmStructuredOutput(type="content", content=response.output_text)

    def __to_json(self, value: Any) -> str:
        return json.dumps(value, indent=2)
