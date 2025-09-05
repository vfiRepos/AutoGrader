import os
import logging
from openai import OpenAI

logging.basicConfig(level=logging.INFO)

def get_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logging.error("❌ OPENAI_API_KEY not found in environment variables.")
        raise RuntimeError("❌ OPENAI_API_KEY not found in environment variables.")
    
    # Log only the first few characters
    logging.info(f"✅ Using OPENAI_API_KEY (starts with {api_key[:6]}...)")
    
    # Explicitly pass the key
    return OpenAI(api_key=api_key)
