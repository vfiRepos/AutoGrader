import os, json, sendgrid
from typing import Dict
from sendgrid.helpers.mail import Mail, Email, To, Content
from openAI_client import get_client



MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "manager@vfi.net")  # fallback if env var not set

class EmailAgent:
    def __init__(self, model="gpt-4o-mini"):
        self.model = model
        self.client = get_client()

    from googleapiclient.discovery import build
from google.oauth2 import service_account
import base64
from email.mime.text import MIMEText
import os

# You’ll need to set GOOGLE_APPLICATION_CREDENTIALS env var to your service account JSON
# and grant domain-wide delegation if you’re sending on behalf of a user.

def gmail_send_message(to_email: str, subject: str, html_body: str, sender: str) -> dict:
    """
    Send an email using the Gmail API.

    Args:
        to_email: Recipient address
        subject: Subject line
        html_body: HTML content
        sender: The user email to send as (must be authorized for service account)

    Returns:
        dict: API response from Gmail
    """

    # Authenticate Gmail API
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES
    )
    delegated_creds = creds.with_subject(sender)

    service = build("gmail", "v1", credentials=delegated_creds)

    # Build MIME message
    message = MIMEText(html_body, "html")
    message["to"] = to_email
    message["from"] = sender
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    # Send the message
    send_result = service.users().messages().send(
        userId="me", body={"raw": raw_message}
    ).execute()

    print(f"📧 Sent email to {to_email}, ID: {send_result['id']}")
    return send_result


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
