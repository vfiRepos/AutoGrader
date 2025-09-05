import time
import logging
from openai import OpenAI
from pydantic_formating import SkillReport
from openAI_client import get_client

logging.basicConfig(level=logging.INFO)


INSTRUCTIONS = """
You are an SVP in equipment finance grading a sales call transcript for **Value Proposition Communication**.

Instructions:
- Did the rep clearly articulate VFI's value proposition?
- Did they explain the benefits of equipment financing vs. alternatives?
- Did they highlight VFI's competitive advantages?
- Did they address the prospect's specific needs and pain points?

IMPORTANT: You must respond with ONLY a JSON object in this exact format:
{
  "items": [
    {
      "skill": "value_prop",
      "grade": "A",
      "reasoning": "Your detailed reasoning here"
    }
  ]
}

Do not include any other text, explanations, or formatting outside the JSON.

Transcript: 
{transcript}
"""

# Initialize OpenAI/Gemini client
client = get_client()


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
                        "skill": "value_prop",
                        "grade": "C",
                        "reasoning": "Error parsing AI response"
                    }
                ]
            })

        elapsed = time.time() - start_time
        logging.info(f"✅ Grading for {self.name} completed in {elapsed:.2f}s")
        return result


# Example instantiation for Value Proposition
value_prop_agent = Agent(
    name="Value Proposition Grader",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini"   # or "gemini-1.5-flash" if using Gemini
)
