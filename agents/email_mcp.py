import asyncio
import sys
from pathlib import Path

from typing import Literal, TypedDict
from pydantic import BaseModel, Field
from datetime import datetime

from langchain_openai import ChatOpenAI

from utils.email_handlers import get_triage_instructions, get_action_instructions, parse_email, format_email_markdown

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.types import Command
from dotenv import load_dotenv

load_dotenv("../.env")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools

# Get absolute path to the MCP server script
_mcp_server_path = Path(__file__).parent.parent / "tools" / "email_mcp.py"
server_params = StdioServerParameters(
    command=sys.executable,  # Use the same Python interpreter (important for venv)
    args=["-u", str(_mcp_server_path.absolute())],  # -u for unbuffered output (required for stdio)
)

# ----- State & Schemas -----
class RouterSchema(BaseModel):
    """Analyze the unread email and route it according to its content."""
    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )
    classification: Literal["ignore", "respond", "notify"] = Field(
        description=("The classification of an email: 'ignore' for irrelevant emails, "
                     "'notify' for important information that doesn't need a response, "
                     "'respond' for emails that need a reply"),
    )

class StateInput(TypedDict):
    email_input: dict

class State(MessagesState):
    email_input: dict
    classification_decision: Literal["ignore", "respond", "notify"]

# ----- Node and edge function templates (pass context in setup) -----
def create_llm_call(llm_with_tools):
    def llm_call(state: State):
        agent_system_prompt = get_action_instructions()
        return {
            "messages": [
                llm_with_tools.invoke([
                    {"role": "system", "content": agent_system_prompt.format(today=datetime.now().strftime("%Y-%m-%d"))}
                ] + state["messages"])
            ]
        }
    return llm_call

def create_tool_node(tools_by_name):
    async def tool_node(state: State):
        result = []
        for tool_call in state["messages"][-1].tool_calls:
            tool = tools_by_name[tool_call["name"]]
            observation = await tool.ainvoke(tool_call["args"])
            result.append({"role": "tool", "content" : observation, "tool_call_id": tool_call["id"]})
        return {"messages": result}
    return tool_node

def should_continue(state: State) -> Literal["Action", "__end__"]:
    """Route to Action, or end if Done tool called"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "Done":
                return END
            else:
                return "Action"

def create_triage_router(llm_router):
    """Create triage_router function with llm_router dependency"""
    def triage_router(state: State) -> Command[Literal["response_agent", "__end__"]]:
        """
        Analyze email content to decide if we should respond, notify, or ignore.
        """
        author, to, subject, email_thread = parse_email(state["email_input"])
        system_prompt = get_triage_instructions()

        user_prompt = """
Please determine how to handle the below email thread:

From: {author}
To: {to}
Subject: {subject}
{email_thread}""".format(
            author=author, to=to, subject=subject, email_thread=email_thread
        )

        # Create email markdown for Agent Inbox in case of notification  
        email_markdown = format_email_markdown(subject, author, to, email_thread)

        # Run the router LLM
        result = llm_router.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        # Decision
        classification = result.classification

        if classification == "respond":
            goto = "response_agent"
            # Add the email to the messages
            update = {
                "classification_decision": result.classification,
                "messages": [{"role": "user",
                                "content": f"Respond to the email: {email_markdown}"
                            }],
            }
        elif result.classification == "ignore":
            update =  { "classification_decision": result.classification}
            goto = END
        elif result.classification == "notify":
            update = { "classification_decision": result.classification}
            goto = END
        else:
            raise ValueError(f"Invalid classification: {result.classification}")
        return Command(goto=goto, update=update)
    return triage_router

# ----- Main setup function -----
async def setup_email_assistant():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            tools_by_name = {tool.name: tool for tool in tools}
            llm = ChatOpenAI(model="gpt-4.1", temperature=0.0)
            llm_with_tools = llm.bind_tools(tools, tool_choice="any", parallel_tool_calls=False)
            llm_router = llm.with_structured_output(RouterSchema)

            # Build response agent workflow
            agent_builder = StateGraph(State)
            agent_builder.add_node("agent", create_llm_call(llm_with_tools))
            agent_builder.add_node("tools", create_tool_node(tools_by_name))
            agent_builder.add_edge(START, "agent")
            agent_builder.add_conditional_edges(
                "agent",
                should_continue,
                {
                    # Name returned by should_continue : Name of next node to visit
                    "Action": "tools",
                    END: END,
                },
            )
            agent_builder.add_edge("tools", "agent")

            # Compile the agent
            agent = agent_builder.compile()

            # Build overall workflow with triage router
            triage_router = create_triage_router(llm_router)
            overall_workflow = (
                StateGraph(State, input=StateInput)
                .add_node(triage_router)
                .add_node("response_agent", agent)
                .add_edge(START, "triage_router")
            )
            email_assistant = overall_workflow.compile()
            yield email_assistant

# Usage example:
# async for email_assistant in setup_email_assistant():
#     # use email_assistant here
#     # session stays open while in this block
#     pass