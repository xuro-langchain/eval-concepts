# Eval Concepts


## Introduction
In this notebook, we'll set up 2 applications
1. ELI5: A simple app to demonstrate the basics of tracing and evaluation, to illustrate AI development workflows
2. MultiAgent: A more complex agent to demonstrate advanced evaluation concepts


## Pre-work

### Create .env file

Follow the example in .env.example to fill in the necessary information to run the application.

### Install dependencies

Create a virtual enviornment
```
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies
```
pip install -r requirements.txt
```

Then you're ready to run the notebooks!

### The Notebooks

#### Basics
The simple agent is available in the ```basics``` folder, and the exercise can be run through the eli5 notebook.
ELI5 is a simple RAG pipeline designed to answer questions in a way a 5-year-old could understand.

#### Advanced
The complex agent is available in the ```advanced``` folder, and eval exercises can be run through the notebooks 
in the folder. MultiAgent is a customer service assistant for a digital music store, and has tools to 
query songs and invoices. 

The multiagent is a supervisor architecture defined in ```multiagent.py```, and its tools live in ```multiagent_tools.py```