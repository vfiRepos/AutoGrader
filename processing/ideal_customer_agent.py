import time
import logging
from openai import OpenAI
from pydantic_formating import SkillReport
from openAI_client import get_client

logging.basicConfig(level=logging.INFO)


INSTRUCTIONS = """
You are an SVP in equipment finance grading a sales call transcript for **Ideal Customer Profile (ICP) Alignment**.

Instructions:
- Did the rep identify if the prospect fits VFI's ICP?
- Did they ask about company size, industry, growth stage?
- Did they explore if the prospect has the right pain points?
- Did they qualify the prospect's funding needs and timeline?

IMPORTANT: You must respond with ONLY a JSON object in this exact format:
{
  "items": [
    {
      "skill": "icp",
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
                        "skill": "icp",
                        "grade": "C",
                        "reasoning": "Error parsing AI response"
                    }
                ]
            })

        elapsed = time.time() - start_time
        logging.info(f"✅ Grading for {self.name} completed in {elapsed:.2f}s")
        return result


# Example instantiation for ICP Alignment
icp_agent = Agent(
    name="ICP Alignment Grader",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini"   # or "gemini-1.5-flash" if using Gemini
)
