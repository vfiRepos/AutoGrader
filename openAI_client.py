import os
from openai import OpenAI

def get_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("❌ OPENAI_API_KEY is not set in environment variables.")
    return OpenAI(api_key=api_key)
