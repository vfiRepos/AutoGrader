import time
import logging
import json
import re
import google.generativeai as genai
from pydantic_formating import SkillReport

logging.basicConfig(level=logging.INFO)


def clean_json(raw: str) -> str:
    """Remove markdown code fences and return raw JSON string."""
    return re.sub(r"^```[a-zA-Z]*\n|\n```$", "", raw.strip())


class Agent:
    def __init__(self, name: str, instructions: str, model: str = "gemini-1.5-flash", tools=None):
        self.name = name
        self.instructions = instructions
        self.model = genai.GenerativeModel(model)
        self.tools = tools or []

    def run(self, transcript: str, max_retries: int = 3):
        start_time = time.time()
        ai_response = None

        # Build the complete prompt with instructions and JSON requirements
        prompt = f"""
        {self.instructions}

        IMPORTANT: You must respond with ONLY valid JSON.
        Do NOT include ```json fences, code blocks, or any other text.
        Respond with pure JSON in this format:
        {{
          "items": [
            {{
              "skill": "{self.name.lower().replace(" ", "_")}",
              "grade": "A",
              "reasoning": "Your detailed reasoning here"
            }}
          ]
        }}

        Transcript:
        {transcript}
        """

        for _ in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                ai_response = (response.text or "").strip()

                # Clean and parse JSON
                cleaned = clean_json(ai_response)
                result = SkillReport.model_validate_json(cleaned)

                logging.info(f"✅ {self.name}: {result.items[0].grade}")
                return result

            except Exception as e:
                if _ == max_retries - 1:  # Only log on final failure
                    logging.error(f"❌ {self.name}: Failed after {max_retries} attempts, using fallback.")
                time.sleep(2 * (_ + 1))  # backoff before retry

        # Fallback result
        return SkillReport.model_validate({
            "items": [
                {
                    "skill": self.name.lower().replace(" ", "_"),
                    "grade": "C",
                    "reasoning": "Error parsing AI response after retries"
                }
            ]
        })
