import time
import logging
from openai import OpenAI
from openAI_client import get_client

logging.basicConfig(level=logging.INFO)


class Agent:
    def __init__(self, name: str, instructions: str, model: str, tools=None):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.tools = tools or []

    def run(self, transcript: str, response_format=None):
        start_time = time.time()
        logging.info(f"🔄 Starting grading for {self.name}...")

        client = get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": transcript}],
            response_format=response_format,
        )

        ai_response = response.choices[0].message.content
        logging.info(f"🤖 AI Response (truncated): {ai_response[:200]}...")

        elapsed = time.time() - start_time
        logging.info(f"✅ Grading for {self.name} completed in {elapsed:.2f}s")
        return ai_response


def build_synthesizer(graded_results: dict, model: str = "gpt-4o-mini"):
    # Flatten dict into readable text
    grades_text = "\n".join(
        f"{skill_name.replace('_', ' ').title()}: {report.items[0].grade} — {report.items[0].reasoning}"
        for skill_name, report in graded_results.items()
    )

    instructions = f"""
    You are the synthesizer. Combine the following graded skill areas into one final evaluation.

    Skill grades:
    {grades_text}

    Provide a final grade (A–F) with reasoning.
    """

    return Agent(
        name="Final Synthesizer",
        instructions=instructions,
        model=model,
    )
