
from openai import OpenAI
client = OpenAI()

class Agent:
    def __init__(self, name: str, instructions: str, model: str, tools=None):
        self.agent = name
        self.input = instructions
        self.model = model
        self.tools = tools or []

    def run(self, transcript: str, response_format=None):
        prompt = self.instructions.format(transcript=transcript)
        return client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format=response_format,
        )
