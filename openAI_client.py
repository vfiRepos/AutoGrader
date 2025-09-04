# openai_client.py
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env early
load_dotenv()

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("❌ OPENAI_API_KEY is not set. Check your .env file.")
    return OpenAI(api_key=api_key)

