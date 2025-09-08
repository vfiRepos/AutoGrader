import time
import logging
from openai import OpenAI
from pydantic_formating import SkillReport
from gemini_client import get_gemini_client


INSTRUCTIONS = """
Grade the rep's **call control and next-step setting**.

Did they:
- Balance listening vs. speaking?
- Guide the conversation without dominating?
- Set a clear follow-up step (e.g., criteria sheet, second call)?

IMPORTANT: You must respond with ONLY a JSON object in this exact format:
{{
  "items": [
    {{
      "skill": "call_control",
      "grade": "A",
      "reasoning": "Your detailed reasoning here"
    }}
  ]
}}

Do not include any other text, explanations, or formatting outside the JSON.

Transcript:
{transcript}
"""


# Initialize OpenAI/Gemini client (via your wrapper so you can switch later)
client = get_gemini_client()


class Agent:
    def __init__(self, name: str, instructions: str, model: str, tools=None):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.tools = tools or []

    def run(self, transcript: str, response_format=None):
        start_time = time.time()
        logging.info(f"🔄 Starting grading for {self.name}...")

        prompt = self.instructions.format(transcript=transcript)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format=response_format,
        )

        ai_response = response.choices[0].message.content
        logging.info(f"🤖 AI Response (truncated): {ai_response[:200]}...")

        try:
            result = SkillReport.model_validate_json(ai_response)
        except Exception as e:
            logging.error(f"❌ JSON parsing failed: {e}")
            logging.debug(f"🔍 Raw response: {ai_response}")
            result = SkillReport.model_validate({
                "items": [
                    {
                        "skill": "call_control",
                        "grade": "C",
                        "reasoning": "Error parsing AI response"
                    }
                ]
            })

        elapsed = time.time() - start_time
        logging.info(f"✅ Grading for {self.name} completed in {elapsed:.2f}s")
        return result


# Example instantiation for call control
call_control_agent = Agent(
    name="Call Control Grader",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini"   # or "gemini-1.5-flash" if using Gemini
)
