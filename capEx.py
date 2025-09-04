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
Grade the rep's **positioning of VFI as a growth CapEx partner**.

Did the rep:
- Distinguish VFI from banks?
- Emphasize funding fixed assets (equipment, IT, software, leasehold improvements)?
- Explain post-close liquidity benefits?
- Align with PE sponsors or CFO priorities?

IMPORTANT: You must respond with ONLY a JSON object in this exact format:
{{
  "items": [
    {{
      "skill": "positioning",
      "grade": "A",
      "reasoning": "Your detailed reasoning here"
    }}
  ]
}}

Do not include any other text, explanations, or formatting outside the JSON.

Transcript:
{transcript}
"""

async def positioning_grader_agent(transcript: str):
    start_time = time.time()
    print("🔄 Starting Positioning Grading...")
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
                    "skill": "positioning",
                    "grade": "C",
                    "reasoning": "Error parsing AI response"
                }
            ]
        })
    
    elapsed = time.time() - start_time
    print(f"✅ Positioning Grading completed in {elapsed:.2f}s")
    return result
