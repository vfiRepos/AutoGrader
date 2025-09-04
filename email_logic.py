import os, json, sendgrid
from typing import Dict
from openai import OpenAI
from sendgrid.helpers.mail import Mail, Email, To, Content
from openAI_client import get_client



MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "manager@vfi.net")  # fallback if env var not set

class EmailAgent:
    def __init__(self, model="gpt-4o-mini"):
        self.model = model
        self.client = get_client()

    def email_tool(self, subject: str, html_body: str) -> Dict[str, str]:
        """Send an email via SendGrid to a fixed manager address."""
        sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
        from_email = Email("gusdaskalakis@gmail.com")   # must be a verified sender or domain
        to_email = To('gusdaskalakis@gmail.com')            # <-- always the same recipient
        content = Content("text/html", html_body)
        mail = Mail(from_email, to_email, subject, content).get()
        response = sg.client.mail.send.post(request_body=mail)
        print("📧 Email response", response.status_code)
        return {"status": "success", "code": response.status_code}

    def run(self, results: dict, synthesis_result: str):

        # Build instructions
        skill_summary = "\n".join([f"- {skill}: {grade}" for skill, grade in results.items()])
        instructions = f"""
        Per-skill results:
        {skill_summary}

        Synthesizer summary:
        {synthesis_result}

        include all of the results in the email. 
        Include the name of the salesperson and the date of the call, which is just today's date 
        in the subject line. 
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": instructions}],
            tools=[{
                "type": "function",
                "function": {
                    "name": "email_tool",
                    "description": "Send an email with results to the sales manager",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string"},
                            "html_body": {"type": "string"}
                        },
                        "required": ["subject", "html_body"]
                    }
                }
            }]
        )

        message = response.choices[0].message

        if getattr(message, "tool_calls", None):
            for tool_call in message.tool_calls:
                if tool_call.function.name == "email_tool":
                    raw_args = tool_call.function.arguments or "{}"
                    args = json.loads(raw_args)
                    subject = args.get("subject")
                    html_body = args.get("html_body")

                    if not all([subject, html_body]):
                        raise ValueError(f"Missing fields in tool args: {args}")

                    return {"status": "sent", "details": self.email_tool(subject, html_body)}

        # If the model doesn’t call the tool, just log its draft response
        return {"status": "skipped", "content": (message.content or "")[:200]}
