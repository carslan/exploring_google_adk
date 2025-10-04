# my_openai_llm.py
import json
import os
import re
import uuid
from typing import AsyncGenerator, Any, Optional, Literal, Union

from google.adk.models import LlmResponse, BaseLlm, LlmRequest
from google.genai import types
from google.genai.types import Part, Content, FunctionDeclaration
from openai import AsyncOpenAI
from openai.types.responses import Response
from pydantic import BaseModel, Field

key = "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"


# --- Models for structured reasoning and tool calls ---
class SuggestedParameter(BaseModel):
    value: Any = Field(description="Actual and clear value of the parameter")
    tool: str = Field(description="Name of the tool that might provide the value")
    param: str = Field(description="Source parameter of the value in the tool response")
    note: Optional[str] = Field(None, description="Explanation or extraction logic if needed")


class BaseLlmToolCall(BaseModel):
    tool_name: str = Field(description="Name of the tool to invoke")
    args: Union[dict[str, Any], dict[str, SuggestedParameter]] = Field(description="Arguments for the tool")
    reasoning: str = Field(description="Why this tool was selected and how parameters were chosen")


class BaseLlmStructuredOutput(BaseModel):
    type: Literal["tool_call", "content"] = "content"
    content: Optional[Any] = None
    tool_calls: list[BaseLlmToolCall] = Field(default_factory=list)
    suggested_tool_calls: list[BaseLlmToolCall] = Field(default_factory=list)

    def is_tool_call(self) -> bool:
        return self.type == "tool_call" and bool(self.tool_calls)

    def to_tool_calls(self) -> list[Part]:
        calls = []
        for call in self.tool_calls:
            fn_call = types.Part.from_function_call(name=call.tool_name, args=call.args)
            fn_call.function_call.id = str(uuid.uuid4())
            calls.append(fn_call)
        return calls

    def selected_tool_reasoning(self) -> dict:
        return {tool.tool_name: tool.reasoning for tool in self.tool_calls}


# --- Core LLM class ---
class LlmModel(BaseLlm):
    """Minimal OpenAI-backed LLM for Google ADK"""
    model: str = "gpt-5-mini"

    async def generate_content_async(
            self,
            request: LlmRequest,
            stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        """Main ADK entrypoint."""
        llm_output = await self._send_request(request, stream=stream)

        if llm_output.is_tool_call():
            yield LlmResponse(
                custom_metadata={
                    "selected_tool_reasoning": llm_output.selected_tool_reasoning(),
                    "suggested_tool_calls": [st.model_dump() for st in llm_output.suggested_tool_calls],
                },
                content=Content(role="assistant", parts=llm_output.to_tool_calls()),
            )
        else:
            yield LlmResponse(
                content=types.Content(
                    role="assistant",
                    parts=[Part.from_text(text=str(llm_output.content))],
                )
            )

    async def _send_request(self, request: LlmRequest, stream: bool = False) -> BaseLlmStructuredOutput:
        """Prepare prompt and call OpenAI API."""
        document = self._prepare_tool_docs(request)

        system_prompt = f"""You are a helper agent for an orchestrator. Your job is to decide whether to:
1. Invoke one or more tools, or
2. Provide a direct answer (if no tool call is needed).

Below are the available tools:
{document}

# Expected Output
## Tool Call Output Rules
- NEVER use sample/example parameters from docs.
- ALWAYS provide valid parameter values.
- You must only call tools whose parameters can be filled from current context.
- Respect the expected JSON schema below.

### Output JSON
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
Return ONLY valid JSON. No markdown, no explanations (When it is only tool call(s)).

## None Tool Call Output Rules
Provide honest, correct answers."""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._normalize_request_contents(request))

        client = AsyncOpenAI(api_key=key)
        response: Response = await client.responses.create(model=self.model, input=messages)

        return self._parse_response(response)

    # --- helper functions ---
    def _prepare_tool_docs(self, request: LlmRequest) -> str:
        docs = []
        for tool_name, tool in request.tools_dict.items():
            fd: FunctionDeclaration = tool.function_declaration
            schema = fd.parameters_json_schema
            try:
                if hasattr(schema, "model_json_schema"):
                    schema = schema.model_json_schema()
                elif hasattr(schema, "schema"):
                    schema = schema.schema()
                elif isinstance(schema, type):
                    schema = schema.__dict__
                schema_json = json.dumps(schema, indent=2)
            except Exception as e:
                schema_json = f"<unable to serialize schema: {e}>"

            docs.append(f"### Tool: {tool_name}\n{tool.description}\nSchema:\n{schema_json}\n")
        return "\n".join(docs)

    def _normalize_request_contents(self, request: LlmRequest) -> list[dict]:
        """Flatten ADK Content into OpenAI-style messages."""
        messages = []
        for content in request.contents:
            for part in content.parts:
                if part.function_call:
                    messages.append({
                        "role": content.role,
                        "content": self._to_json({
                            "action": "tool_call",
                            "tool": part.function_call.name,
                            "args": part.function_call.args,
                            "tool_call_id": part.function_call.id,
                        }),
                    })
                elif part.function_response:
                    fn_decl: FunctionDeclaration = request.tools_dict[part.function_response.name].function_declaration
                    schema = fn_decl.response_json_schema
                    response_data = part.function_response.response.get("result", {})
                    normalized = self._normalize_tool_output(response_data, schema)
                    messages.append({
                        "role": content.role,
                        "content": self._to_json({
                            "action": "tool_call_response",
                            "tool_call_id": part.function_response.id,
                            "output": normalized,
                        }),
                    })
                else:
                    messages.append({"role": content.role, "content": part.text})
        return messages

    def _normalize_tool_output(self, output: Any, schema: BaseModel) -> list[dict]:
        """Normalize a tool response using its declared schema."""
        if isinstance(output, list):
            return [schema(**item).model_dump() for item in output]
        return [schema(**output).model_dump()]

    def _parse_response(self, response: Response) -> BaseLlmStructuredOutput:
        """Extract and parse structured output safely."""
        text = response.output_text
        if isinstance(text, list):
            text = text[0]

        match = re.search(r"\{.*}", text, re.DOTALL)
        if not match:
            return BaseLlmStructuredOutput(type="content", content=text)

        try:
            data = json.loads(match.group(0))
            return BaseLlmStructuredOutput(**data)
        except Exception as e:
            return BaseLlmStructuredOutput(type="content", content=f"Invalid JSON from model: {e}\n{text}")

    def _to_json(self, value: Any) -> str:
        return json.dumps(value, indent=2)
