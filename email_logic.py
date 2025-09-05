import os, json, sendgrid
from typing import Dict
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

    def run(self, results: dict, synthesis_result: str, transcript: str, file_name: str):

        
        # Just use the file name exactly as it is
        transcript_name = file_name

        # Build skill summary
        skill_summary = "\n".join([f"- {skill}: {grade}" for skill, grade in results.items()])

        # Build instructions for the model
        instructions = f"""
        Sales call grading report.

        Transcript file: {transcript_name}

        Per-skill results:
        {skill_summary}

        Synthesizer summary:
        {synthesis_result}

        Original transcript:
        {transcript}

        Include all of the results in the email. 
        Use the transcript file name ({transcript_name}) in the subject line.
        include all of the grading results in the email plus the original transcript for reference.
  
 
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

                    
                    # ✅ Append transcript yourself for reliability
                    html_body += f"""
                    <hr>
                    <h3>Original Transcript ({transcript_name})</h3>
                    <pre style="white-space: pre-wrap; font-family: monospace;">
                    {transcript}
                    </pre>
                    """

                    return {"status": "sent", "details": self.email_tool(subject, html_body)}

        return {"status": "skipped", "content": (message.content or "")[:200]}
