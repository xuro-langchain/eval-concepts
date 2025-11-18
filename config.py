import os
import requests
from typing import Dict
from dotenv import load_dotenv
from langsmith import Client, traceable

load_dotenv(".env")

client = Client()

LANGSMITH_API_URL = os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def auth_headers() -> Dict[str, str]:
    if not LANGSMITH_API_KEY:
        raise RuntimeError("LANGSMITH_API_KEY is required in environment.")
    return {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json",
    }
