import os
import logging
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

def init_gemini():
    api_key = os.environ.get("GENAI_API_KEY")
    if not api_key:
        logging.error("❌ GENAI_API_KEY not found in environment variables.")
        raise RuntimeError("❌ GENAI_API_KEY not found in environment variables.")
    
    logging.info(f"✅ Using GENAI_API_KEY (starts with {api_key[:6]}...)")
    genai.configure(api_key=api_key)
