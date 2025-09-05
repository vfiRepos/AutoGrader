import os
import logging
from openai import OpenAI

logging.basicConfig(level=logging.INFO)

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logging.error("❌ GEMINI_API_KEY not found in environment variables.")
        raise RuntimeError("❌ GEMINI_API_KEY not found in environment variables.")
    
    logging.info(f"✅ Using GEMINI_API_KEY (starts with {api_key[:6]}...)")

    return OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
