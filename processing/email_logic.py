import os
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2 import service_account

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def build_email_with_attachment(to_email, subject, html_body, transcript, sender):
    message = MIMEMultipart()
    message["to"] = to_email
    message["from"] = sender
    message["subject"] = subject

    # HTML part
    message.attach(MIMEText(html_body, "html"))

    # Transcript as attachment
    attachment = MIMEBase("text", "plain")
    attachment.set_payload(transcript.encode("utf-8"))
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename="transcript.txt")
    message.attach(attachment)

    return message


def gmail_send_message(mime_message, sender: str) -> dict:
    """
    Send a MIME email using Gmail API.
    """

    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    # Authenticate Gmail API
    creds = service_account.Credentials.from_service_account_file(
    "/secrets/gmail-sa-key.json", scopes=SCOPES
)
    delegated_creds = creds.with_subject(sender)
    service = build("gmail", "v1", credentials=delegated_creds)

    # Encode the full MIME message
    raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

    send_result = service.users().messages().send(
        userId="me", body={"raw": raw_message}
    ).execute()

    print(f"📧 Sent email from {sender} to {mime_message['to']}, Gmail ID: {send_result['id']}")
    return send_result