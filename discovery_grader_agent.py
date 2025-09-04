from webbrowser import get
from pydantic_formating import SkillReport
from openai import OpenAI
import os
from dotenv import load_dotenv
import asyncio
import time
import json
from openAI_client import get_client

# Load environment variables


INSTRUCTIONS = """
You are an SVP in equipment finance grading a sales call transcript for **Discovery Questions**.

Instructions:
- Did the rep ask strategic, open-ended questions?
- Did they inquire about the business, capital structure, deal flow, pain points?
- Did they explore decision-maker roles?
- Did they ask about the prospect's Ideal Customer Profile (ICP) and overlaps?

IMPORTANT: You must respond with ONLY a JSON object in this exact format:
{{
  "items": [
    {{
      "skill": "discovery",
      "grade": "A",
      "reasoning": "Your detailed reasoning here"
    }}
  ]
}}

Do not include any other text, explanations, or formatting outside the JSON.

Transcript: 
{transcript}
"""

async def discovery_grader_agent(transcript: str):
    start_time = time.time()
    print("🔄 Starting Discovery Grading...")

    client = get_client()

    
    prompt = INSTRUCTIONS.format(transcript=transcript)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Debug: Print what the AI actually returned
    ai_response = response.choices[0].message.content
    print(f"🤖 AI Response: {ai_response[:200]}...")
    
    try:
        result = SkillReport.model_validate_json(ai_response)
    except Exception as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"🔍 Raw response: {ai_response}")
        # Create a fallback result
        result = SkillReport.model_validate({
            "items": [
                {
                    "skill": "discovery",
                    "grade": "C",
                    "reasoning": "Error parsing AI response"
                }
            ]
        })
    
    elapsed = time.time() - start_time
    print(f"✅ Discovery Grading completed in {elapsed:.2f}s")
    return result
