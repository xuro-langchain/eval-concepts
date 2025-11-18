# Environment Dependencies
from dotenv import load_dotenv

# Memory and Checkpoint Dependencies
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# State Dependencies
from typing import Annotated, List
from typing_extensions import TypedDict, Optional, NotRequired
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from pydantic import BaseModel, Field

# Prebuilts
from langchain.agents import create_agent
from langgraph.types import interrupt

# Tools
from langchain.tools import tool, ToolRuntime
from tools.multi_basic import invoice_tools, music_tools
from utils.multi_basic import get_customer_id_from_identifier


load_dotenv(dotenv_path="../.env", override=True)
model = ChatOpenAI(model="o3-mini")


# Initializing long term memory store 
in_memory_store = InMemoryStore()
# Initializing checkpoint for thread-level memory 
checkpointer = MemorySaver()



class State(TypedDict):
    customer_id: NotRequired[str]
    messages: Annotated[list[AnyMessage], add_messages]

## Defining Invoice Subagent --------------------------------------------------------------------
invoice_subagent_prompt = """
    You are a subagent among a team of assistants. You are specialized for retrieving and processing invoice information. You are routed for invoice-related portion of the questions, so only respond to them.. 

    You have access to three tools. These tools enable you to retrieve and process invoice information from the database. Here are the tools:
    - get_invoices_by_customer_sorted_by_date: This tool retrieves all invoices for a customer, sorted by invoice date.
    - get_invoices_sorted_by_unit_price: This tool retrieves all invoices for a customer, sorted by unit price.
    - get_employee_by_invoice_and_customer: This tool retrieves the employee information associated with an invoice and a customer.
    
    If you are unable to retrieve the invoice information, inform the customer you are unable to retrieve the information, and ask if they would like to search for something else.
    
    CORE RESPONSIBILITIES:
    - You must have the customer's ID before you can retrieve any information.
    - Retrieve and process invoice information from the database
    - Provide detailed information about invoices, including customer details, invoice dates, total amounts, employees associated with the invoice, etc. when the customer asks for it.
    - Always maintain a professional, friendly, and patient demeanor
"""
 
invoice_subagent = create_agent(
    model=model, tools=invoice_tools, 
    name="invoice_information_subagent",
    system_prompt=invoice_subagent_prompt, 
    state_schema=State, 
    checkpointer=checkpointer, store=in_memory_store)

## Defining Music Subagent --------------------------------------------------------------------
music_subagent_prompt = """
    You are a member of the assistant team, your role specifically is to focused on helping customers discover and learn about music in our digital catalog. 
    If you are unable to find playlists, songs, or albums associated with an artist, it is okay. 
    Just inform the customer that the catalog does not have any playlists, songs, or albums associated with that artist.
    
    CORE RESPONSIBILITIES:
    - Search and provide accurate information about songs, albums, artists, and playlists
    - Offer relevant recommendations based on customer interests
    - Handle music-related queries with attention to detail
    - Help customers discover new music they might enjoy
    - You are routed only when there are questions related to music catalog; ignore other questions. 
    
    SEARCH GUIDELINES:
    1. Always perform thorough searches before concluding something is unavailable
    2. If exact matches aren't found, try:
       - Checking for alternative spellings
       - Looking for similar artist names
       - Searching by partial matches
       - Checking different versions/remixes
    3. When providing song lists:
       - Include the artist name with each song
       - Mention the album when relevant
       - Note if it's part of any playlists
       - Indicate if there are multiple versions
    4. If results aren't available, DO NOT MAKE ANY SONGS, ALBUMS, OR ARTISTS UP. Just say there are no results.
    
    Message history is also attached.  
    """

music_subagent = create_agent(
    model=model, tools=music_tools, 
    name="music_subagent",
    system_prompt=music_subagent_prompt, 
    state_schema=State, 
    checkpointer=checkpointer, store=in_memory_store)


# Defining Supervisor Agent --------------------------------------------------------------------
supervisor_prompt = """
    You are an expert customer support assistant for a digital music store. 
    You are dedicated to providing exceptional service and ensuring customer queries are answered thoroughly. 
    You have a team of subagents that you can use to help answer queries from customers. 
    Your primary role is to serve as a supervisor/planner for this multi-agent team that helps answer queries from customers. 

    Your team is composed of two subagents that you can use to help answer the customer's request:
    1. music_catalog_information_subagent: this subagent has access to user's saved music preferences. It can also retrieve information about the digital music store's music 
    catalog (albums, tracks, songs, etc.) from the database. 
    3. invoice_information_subagent: this subagent is able to retrieve information about a customer's past purchases or invoices 
    from the database. 

    If the customer's request is related to music or invoices, you MUST route the request to the appropriate subagent. 
    If the customer's request is not related to music or invoices, you can respond to the customer yourself. 

    Based on the existing steps that have been taken in the messages, your role is to generate the next subagent that needs to be called. 
    This could be one step in an inquiry that needs multiple sub-agent calls.
"""

@tool(
    name_or_callable="invoice_information_subagent",
    description="""
        An agent that can assistant with all invoice-related queries. It can retrieve information about a customers past purchases or invoices.
        """
)
def call_invoice_information_subagent(runtime: ToolRuntime, query: str):
    print('made it here')
    print(f"invoice subagent input: {query}")
    result = invoice_subagent.invoke({
        "messages": [{"role": "user", "content": query}],
        "customer_id": runtime.state.get("customer_id", {})
    })
    subagent_response = result["messages"][-1].content
    return subagent_response

@tool(
    name_or_callable="music_catalog_subagent",
    description="""
        An agent that can assistant with all music-related queries. This agent has access to user's saved music preferences. It can also retrieve information about the digital music store's music 
        catalog (albums, tracks, songs, etc.) from the database. 
        """
)
def call_music_catalog_subagent(runtime: ToolRuntime, query: str):
    result = music_subagent.invoke({
        "messages": [{"role": "user", "content": query}],
        "customer_id": runtime.state.get("customer_id", {})
    })
    subagent_response = result["messages"][-1].content
    return subagent_response

supervisor = create_agent(
    model=model, 
    tools=[call_invoice_information_subagent, call_music_catalog_subagent], 
    name="supervisor",
    system_prompt=supervisor_prompt, 
    state_schema=State, 
)


# Adding Human in the Loop --------------------------------------------------------------------
class UserInput(BaseModel):
    """Schema for parsing user-provided account information."""
    identifier: str = Field(description = "Identifier, which can be a customer ID, email, or phone number.")

structured_llm = model.with_structured_output(schema=UserInput)
structured_system_prompt = """You are a customer service representative responsible for extracting customer identifier.\n 
Only extract the customer's account information from the message history. 
If they haven't provided the information yet, return an empty string for the file"""



# Node
def verify_info(state: State, config: RunnableConfig):
    """Verify the customer's account by parsing their input and matching it with the database."""

    if state.get("customer_id") is None: 
        system_instructions = """You are a music store agent, where you are trying to verify the customer identity 
        as the first step of the customer support process. 
        Only after their account is verified, you would be able to support them on resolving the issue. 
        In order to verify their identity, one of their customer ID, email, or phone number needs to be provided.
        If the customer has not provided their identifier, please ask them for it.
        If they have provided the identifier but cannot be found, please ask them to revise it."""

        user_input = state["messages"][-1] 
    
        # Parse for customer ID
        parsed_info = structured_llm.invoke([SystemMessage(content=structured_system_prompt)] + [user_input])
    
        # Extract details
        identifier = parsed_info.identifier
    
        customer_id = ""
        # Attempt to find the customer ID
        if (identifier):
            customer_id = get_customer_id_from_identifier(identifier)
    
        if customer_id != "":
            intent_message = SystemMessage(
                content= f"Thank you for providing your information! I was able to verify your account with customer id {customer_id}."
            )
            return {
                  "customer_id": customer_id,
                  "messages" : [intent_message]
                  }
        else:
          response = model.invoke([SystemMessage(content=system_instructions)]+state['messages'])
          return {"messages": [response]}
    else: 
        pass


# Node
def human_input(state: State, config: RunnableConfig):
    """ No-op node that should be interrupted on """
    user_input = interrupt("Please provide input.")
    return {"messages": [user_input]}

# conditional_edge
def should_interrupt(state: State, config: RunnableConfig):
    if state.get("customer_id") is not None:
        return "continue"
    else:
        return "interrupt"
    
# Final Graph --------------------------------------------------------------------
multi_agent_verify = StateGraph(State) # Adding in input state schema 
multi_agent_verify.add_node("verify_info", verify_info)
multi_agent_verify.add_node("human_input", human_input)
multi_agent_verify.add_node("supervisor", supervisor)

multi_agent_verify.add_edge(START, "verify_info")
multi_agent_verify.add_conditional_edges(
    "verify_info",
    should_interrupt,
    {
        "continue": "supervisor",
        "interrupt": "human_input",
    },
)
multi_agent_verify.add_edge("human_input", "verify_info")
multi_agent_verify.add_edge("supervisor", END)
multiagent = multi_agent_verify.compile(name="multi_agent_verify", checkpointer=checkpointer, store=in_memory_store)

multiagent_studio = multi_agent_verify.compile(name="multi_agent_studio")