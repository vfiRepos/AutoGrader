import re
import time
import logging
import google.generativeai as genai
from pydantic_formating import SkillReport

def clean_ai_json(ai_response: str) -> str:
    """Strip Markdown fences and whitespace from model output."""
    return re.sub(r"^```json|```$", "", ai_response.strip(), flags=re.MULTILINE).strip()

class Agent:
    def __init__(self, name: str, instructions: str, model: str = "gemini-1.5-flash"):
        self.name = name
        self.instructions = instructions
        self.model = genai.GenerativeModel(model)

    def run(self, transcript: str, max_retries: int = 3):
        start_time = time.time()
        logging.info(f"🔄 Starting grading for {self.name}...")

        # Force JSON requirement into the prompt
        prompt = f"""
        {self.instructions}

        IMPORTANT: You must respond with ONLY valid JSON.
        Do NOT include ```json fences, code blocks, or commentary.
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

        ai_response = ""
        for attempt in range(1, max_retries + 1):
            try:
                response = self.model.generate_content(prompt)
                ai_response = response.text or ""
                cleaned = clean_ai_json(ai_response)
                result = SkillReport.model_validate_json(cleaned)

                elapsed = time.time() - start_time
                logging.info(f"✅ Grading for {self.name} completed in {elapsed:.2f}s")
                return result

            except Exception as e:
                logging.warning(f"⚠️ Attempt {attempt}/{max_retries} failed: {e}")
                if attempt == max_retries:
                    logging.error(f"❌ Giving up on {self.name}, using fallback.")
                    return SkillReport.model_validate({
                        "items": [
                            {
                                "skill": self.name.lower().replace(" ", "_"),
                                "grade": "C",
                                "reasoning": f"Error parsing AI response: {e}"
                            }
                        ]
                    })
                time.sleep(2 * attempt)  # backoff before retry
