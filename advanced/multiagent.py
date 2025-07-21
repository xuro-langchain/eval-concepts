# Environment Dependencies
from dotenv import load_dotenv

# Memory and Checkpoint Dependencies
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# State Dependencies
from typing_extensions import TypedDict
from langgraph.managed.is_last_step import RemainingSteps
from typing import Annotated, List
from langgraph.graph.message import AnyMessage, add_messages

# Prebuilts
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

# Tools
from multiagent_tools import invoice_tools, music_tools


load_dotenv(dotenv_path="../.env", override=True)
model = ChatOpenAI(model="o3-mini")


# Initializing long term memory store 
in_memory_store = InMemoryStore()
# Initializing checkpoint for thread-level memory 
checkpointer = MemorySaver()



class State(TypedDict):
    customer_id: str
    messages: Annotated[list[AnyMessage], add_messages]
    remaining_steps: RemainingSteps 

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
 
invoice_subagent = create_react_agent(
    model, tools=invoice_tools, 
    name="invoice_information_subagent",
    prompt=invoice_subagent_prompt, 
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

music_subagent = create_react_agent(
    model, tools=music_tools, 
    name="music_subagent",
    prompt=music_subagent_prompt, 
    state_schema=State, 
    checkpointer=checkpointer, store=in_memory_store)


# Defining Multiagent Graph --------------------------------------------------------------------
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


# Create supervisor workflow
supervisor_prebuilt_workflow = create_supervisor(
    agents=[invoice_subagent, music_subagent],
    output_mode="last_message", # alternative is full_history
    model=model,
    prompt=(supervisor_prompt), 
    state_schema=State
)

multiagent = supervisor_prebuilt_workflow.compile(name="music_catalog_subagent", checkpointer=checkpointer, store=in_memory_store)