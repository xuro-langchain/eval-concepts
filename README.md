# Eval Concepts

## Introduction
This repository contains notebooks demonstrating evaluation concepts for LangGraph agents using LangSmith. The notebooks cover different types of evaluations:

1. **Email Agent Evaluations** (`email_basic.ipynb`, `email_mcp.ipynb`): Demonstrates evaluation concepts with an email assistant agent that can triage emails and respond appropriately
2. **Multi-Agent Evaluations** (`multi_thread.ipynb`): Demonstrates multi-turn evaluation concepts with a customer service multi-agent system

## Pre-work

### Create .env file

Create a `.env` file with the necessary environment variables (e.g., `LANGCHAIN_API_KEY`, `OPENAI_API_KEY`, etc.) to run the applications.

### Install dependencies

Create a virtual environment
```
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies
```
pip install -r requirements.txt
```

Then you're ready to run the notebooks!

## The Notebooks

### Email Agent Evaluations

#### `email_basic.ipynb`
This notebook demonstrates three types of evaluations with a basic email assistant agent:

1. **Final Response Evaluations**: Evaluating the complete agent output against success criteria
2. **Single Step Evaluations**: Evaluating individual steps (e.g., triage classification) 
3. **Trajectory Evaluations**: Evaluating the sequence of tool calls made by the agent

The email agent (`agents/email_basic.py`) consists of:
- A **triage step** that classifies emails as "ignore", "respond", or "notify"
- A **response step** that takes actions like checking calendar availability, scheduling meetings, and writing emails

#### `email_mcp.ipynb`
Similar to `email_basic.ipynb`, but uses the Model Context Protocol (MCP) version of the email agent (`agents/email_mcp.py`). This demonstrates how to evaluate agents that use MCP for tool integration.

### Multi-Agent Evaluations

#### `multi_thread.ipynb`
This notebook demonstrates **multi-turn evaluations** using OpenEvals' simulation capabilities. The multi-agent system (`agents/multi_basic.py`) is a customer service assistant for a digital music store with:

- A supervisor agent that routes queries to specialized sub-agents
- **Invoice sub-agent**: Handles invoice-related queries
- **Music sub-agent**: Handles music catalog queries

The notebook shows how to:
- Create simulated user personas
- Run multi-turn conversation simulations
- Evaluate conversations across multiple turns using various metrics (resolution, satisfaction, professionalism, number of turns)