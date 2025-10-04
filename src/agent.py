import asyncio
import uuid

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.genai import types

from llm_model import LlmModel
from src.tools.anomalies_tool import AnomalyTool
from src.tools.transaction_tool import TransactionTool
from src.utilities.open_ai_llm import MyOpenAiLlm


def before_agent(**kwargs):
    print("1: before_agent")
    return None


def after_agent(**kwargs):
    print("6: after_agent")
    return None


def before_model(**kwargs):
    print("2: before_model")
    return None


def after_model(**kwargs):
    print("3: after_model")
    return None


def before_tool(**kwargs):
    print("4: before_tool")
    return None


def after_tool(**kwargs):
    print("5: after_tool")
    return None


transaction_tool = TransactionTool()
anomaly_tool = AnomalyTool()

tools = [transaction_tool, anomaly_tool]

# llm = MyOpenAiLlm()
llm = LlmModel()

output_key = "123-12344213324-12312"

agent = LlmAgent(
    name="AuditAgent",
    model=llm,
    tools=tools,
    instruction="You are an audit agent, you check and investigate the issues to resolve them",
    output_key=output_key, # whatever the model returns under that key gets stored into session state.
    before_agent_callback=before_agent,
    after_agent_callback=after_agent,
    before_model_callback=before_model,
    after_model_callback=after_model,
    before_tool_callback=before_tool,
    after_tool_callback=after_tool,
)

INITIAL_STATE = {"topic": "lets see where this will be"}


async def main():
    # inside tools, context.state
    # LlmAgent[output_key] -> whatever the model returns under that key gets stored into session state.
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    session = await session_service.create_session(app_name="experimental", user_id="che", session_id=session_id, state=INITIAL_STATE)

    runner = Runner(agent=agent, app_name="experimental", session_service=session_service)

    # "Can you check yesterday’s transactions for anomalies and summarize?"
    user_msg = types.Content(role="user", parts=[types.Part(text="Can you check transactions on 2025-10-02 for account ACC-001 to see if there are anomalies and summarize?")])
    # user_msg = types.Content(role="user", parts=[types.Part(text="Can you check yesterday’s transactions for anomalies and summarize?")])
    # user_msg = types.Content(role="user", parts=[types.Part(text="What about those; '123QSF-XE', 'IG89XQE'")])
    events = runner.run(user_id="che", session_id=session_id, new_message=user_msg)

    for event in events:
        if getattr(event, "content", None):
            for part in getattr(event.content, "parts", []):
                if getattr(part, "text", None):
                    result = part.text
                    print(result)

asyncio.run(main())

# before_model: 'e-5f15f9b1-c04c-4c6e-ad40-0abe1f394384'
# after_model: 'e-5f15f9b1-c04c-4c6e-ad40-0abe1f394384'
#               with model response and metadata,
#               state availability
# before_tool:
#               agent_name = {str} 'AuditAgent'
#               function_call_id = {str} '59f31c21-8222-4b86-87cf-2f9864168141'
#               invocation_id = {str} 'e-5f15f9b1-c04c-4c6e-ad40-0abe1f394384'
#               + state
# after_tool:
#               agent_name = {str} 'AuditAgent'
#               function_call_id = {str} '59f31c21-8222-4b86-87cf-2f9864168141'
#               invocation_id = {str} 'e-5f15f9b1-c04c-4c6e-ad40-0abe1f394384'
#               state = {State} <google.adk.sessions.state.State object at 0x000001E0AF52E7F0>
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#               .