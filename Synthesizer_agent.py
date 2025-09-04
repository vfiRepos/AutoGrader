from pydantic_formating import FinalReport 
from dotenv import load_dotenv
from openai import OpenAI
from openAI_client import get_client
import os
import json

# Load .env file
load_dotenv()


def synthesize(graded_results: dict):
    # Flatten dict into readable text
    grades_text = "\n".join(
        f"{skill_name.replace('_', ' ').title()}: {report.items[0].grade} — {report.items[0].reasoning}"
        for skill_name, report in graded_results.items()
    )

    INSTRUCTIONS = f"""
    You are the synthesizer. Combine the following graded skill areas into one final evaluation.

    Skill grades:
    {grades_text}

    Provide a final grade (A–F) with reasoning.
    """

    try:
        client = get_client()  # create client only when needed
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": INSTRUCTIONS}]
        )
        
        synthesis_result = response.choices[0].message.content
        print(f"🔍 Synthesis Result: {synthesis_result}")
        return synthesis_result
        
    except Exception as e:
        print(f"❌ Synthesis failed: {e}")
        return "Synthesis failed - check individual grades above"
