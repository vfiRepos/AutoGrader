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
    def __init__(self, name: str, instructions: str, model: str = "gemini-2.0-flash", tools=None):
        self.name = name
        self.instructions = instructions
        self.model = genai.GenerativeModel(model)
        self.tools = tools or []

    def run(self, transcript: str, max_retries: int = 3, include_metrics: bool = False):
        start_time = time.time()
        ai_response = None

        # Enhanced JSON format for agents that need detailed metrics
        if include_metrics:
            json_format = """
        {{
          "items": [
            {{
              "skill": "{self.name.lower().replace(" ", "_")}",
              "grade": "A",
              "reasoning": "Your detailed reasoning here",
              "count": 0,
              "examples": [],
              "ratio": 0.0
            }}
          ]
        }}"""
        else:
            json_format = """
        {{
          "items": [
            {{
              "skill": "{self.name.lower().replace(" ", "_")}",
              "grade": "A",
              "reasoning": "Your detailed reasoning here"
            }}
          ]
        }}"""

        # Build the complete prompt with instructions and JSON requirements
        prompt = f"""
        {self.instructions}

        IMPORTANT: You must respond with ONLY valid JSON.
        Do NOT include ```json fences, code blocks, or any other text.
        Respond with pure JSON in this format:
        {json_format}

        Transcript:
        {transcript}
        """

        for attempt in range(max_retries):
            try:
                logging.info(f"🤖 {self.name}: Attempt {attempt + 1}/{max_retries} - Calling AI...")
                response = self.model.generate_content(prompt)
                ai_response = (response.text or "").strip()

                logging.info(f"📝 {self.name}: Raw AI Response (first 200 chars): {ai_response[:200]}{'...' if len(ai_response) > 200 else ''}")

                # Clean and parse JSON
                cleaned = clean_json(ai_response)
                logging.info(f"🧹 {self.name}: Cleaned JSON (first 150 chars): {cleaned[:150]}{'...' if len(cleaned) > 150 else ''}")

                # Special handling for specific agents
                if self.name == "Missed Opportunity":
                    try:
                        parsed_json = json.loads(cleaned)
                        if "items" in parsed_json and parsed_json["items"]:
                            item = parsed_json["items"][0]
                            if "examples" in item and isinstance(item["examples"], list):
                                # Convert any dictionary examples to strings
                                processed_examples = []
                                for example in item["examples"]:
                                    if isinstance(example, dict) and example:
                                        # Extract the first value from the dictionary
                                        first_key = next(iter(example.keys()))
                                        processed_examples.append(str(example[first_key]))
                                    elif isinstance(example, str):
                                        processed_examples.append(example)
                                    else:
                                        processed_examples.append(str(example))
                                item["examples"] = processed_examples
                                cleaned = json.dumps(parsed_json)
                                logging.info(f"🔧 {self.name}: Fixed dictionary examples format")
                    except Exception as parse_error:
                        logging.warning(f"⚠️ {self.name}: Could not fix examples format: {parse_error}")
                
                # Special handling for Call Control agent - validate talk ratios
                elif self.name == "Call Control":
                    try:
                        parsed_json = json.loads(cleaned)
                        if "rep_talk_ratio" in parsed_json and "prospect_talk_ratio" in parsed_json:
                            rep_ratio = parsed_json["rep_talk_ratio"]
                            prospect_ratio = parsed_json["prospect_talk_ratio"]
                            total_ratio = rep_ratio + prospect_ratio
                            
                            if total_ratio > 0 and abs(total_ratio - 100) > 1:  # Allow 1% tolerance
                                # Normalize ratios to add up to 100%
                                parsed_json["rep_talk_ratio"] = (rep_ratio / total_ratio) * 100
                                parsed_json["prospect_talk_ratio"] = (prospect_ratio / total_ratio) * 100
                                cleaned = json.dumps(parsed_json)
                                logging.warning(f"⚠️ {self.name}: Talk ratios didn't add up to 100% (was {total_ratio}%), normalized to rep: {parsed_json['rep_talk_ratio']:.1f}%, prospect: {parsed_json['prospect_talk_ratio']:.1f}%")
                    except Exception as parse_error:
                        logging.warning(f"⚠️ {self.name}: Could not validate talk ratios: {parse_error}")

                # Try direct validation first
                try:
                    result = SkillReport.model_validate_json(cleaned)
                    logging.info(f"✅ {self.name}: SUCCESS! Grade: {result.items[0].grade}")
                    logging.info(f"💬 {self.name}: Reasoning: {result.items[0].reasoning[:100]}{'...' if len(result.items[0].reasoning) > 100 else ''}")
                    return result
                except Exception as validation_error:
                    # If direct validation fails, try to parse as dict and use conversion logic
                    logging.warning(f"⚠️ {self.name}: Direct validation failed, trying conversion logic: {validation_error}")
                    try:
                        parsed_dict = json.loads(cleaned)
                        from grading_manager import gradingManager
                        result = gradingManager.convert_to_skill_report(parsed_dict, self.name.lower().replace(" ", "_"))
                        logging.info(f"✅ {self.name}: SUCCESS! Grade: {result.items[0].grade}")
                        logging.info(f"💬 {self.name}: Reasoning: {result.items[0].reasoning[:100]}{'...' if len(result.items[0].reasoning) > 100 else ''}")
                        return result
                    except Exception as conversion_error:
                        logging.error(f"❌ {self.name}: Both validation and conversion failed: {conversion_error}")
                        raise validation_error  # Re-raise the original validation error

            except Exception as e:
                logging.warning(f"⚠️ {self.name}: Attempt {attempt + 1} failed - {str(e)}")

                if attempt == max_retries - 1:  # Only log on final failure
                    logging.error(f"❌ {self.name}: Failed after {max_retries} attempts, using fallback.")
                    if ai_response:
                        logging.error(f"📄 {self.name}: Final AI response that failed parsing: {ai_response[:300]}{'...' if len(ai_response) > 300 else ''}")
                    else:
                        logging.error(f"📄 {self.name}: No AI response received - likely authentication/permission error")
                time.sleep(2 * (attempt + 1))  # backoff before retry

        # Fallback result - agent failed to grade
        return SkillReport.model_validate({
            "items": [
                {
                    "skill": self.name.lower().replace(" ", "_"),
                    "grade": "N/A",
                    "reasoning": "Agent failed to grade - AI service unavailable"
                }
            ]
        })
