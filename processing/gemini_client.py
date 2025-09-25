import os
import logging
import google.generativeai as genai
import google.auth
from google.auth import credentials

logging.basicConfig(level=logging.INFO)

def init_gemini():
    api_key = os.environ.get("GENAI_API_KEY")
    if not api_key:
        logging.error("❌ GENAI_API_KEY not found in environment variables.")
        raise RuntimeError("❌ GENAI_API_KEY not found in environment variables.")
    
    # Strip whitespace and newlines from the API key (more aggressive)
    api_key = api_key.strip().replace('\n', '').replace('\r', '').strip()
    
    logging.info(f"✅ Using GENAI_API_KEY (starts with {api_key[:6]}...)")
    
    # Configure with explicit API key and disable default credentials
    genai.configure(
        api_key=api_key,
        # Disable automatic credential discovery to avoid conflicts
        transport='rest'  # Use REST instead of gRPC to avoid metadata issues
    )
