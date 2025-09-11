# email_logic.py
import os
import json
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.discovery import build
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO)

# Env var name for the secret JSON (recommend this name)
GMAIL_SA_ENVVAR = "GMAIL_SA_KEY"

# Scopes used for Gmail sending
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Default sender domain address (must be allowed for delegation)
DOMAIN_SENDER = "no-reply@vfi.net"


def format_results_html(results_dict, synthesis_result):
    """Format all grader results and final synthesis into an HTML report."""
    html = "<h2>📊 Sales Transcript Grading Results</h2>"

    # Individual agent results
    for skill_name, report in results_dict.items():
        try:
            item = report.items[0]  # SkillReport from Pydantic
            html += f"""
                <div style="margin-bottom:15px;">
                  <h3>{skill_name.replace('_',' ').title()}</h3>
                  <p><b>Grade:</b> {item.grade}</p>
                  <p><b>Reasoning:</b> {item.reasoning}</p>
                </div>
            """
        except Exception as e:
            html += f"<p><b>{skill_name}:</b> ❌ Error formatting result ({e})</p>"

    # Final synthesis
    try:
        synth_item = synthesis_result.items[0]
        html += """
            <hr>
            <h2>⭐ Final Synthesis</h2>
            <p><b>Final Grade:</b> {grade}</p>
            <p>{reasoning}</p>
        """.format(
            grade=synth_item.grade,
            reasoning=synth_item.reasoning,
        )
    except Exception as e:
        html += f"<p>❌ Error formatting synthesis result ({e})</p>"

    return html


def _load_sa_credentials(scopes=GMAIL_SCOPES):
    """
    Load service account info from an environment variable containing the JSON.
    (Cloud Functions secret injection should set env var GMAIL_SA_KEY to the JSON string.)
    """
    raw = os.environ.get(GMAIL_SA_ENVVAR)
    if not raw:
        raise RuntimeError(
            f"Service account JSON not found in env var {GMAIL_SA_ENVVAR}. "
            "Deploy must map the secret into that env var."
        )
    sa_info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
    return creds


def gmail_service_for_sender(sender: str):
    """
    Return a gmail API client that impersonates `sender`.
    Caller must ensure the service account has domain-wide delegation and admin granted access.
    """
    creds = _load_sa_credentials()
    delegated = creds.with_subject(sender)
    return build("gmail", "v1", credentials=delegated, cache_discovery=False)


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


def gmail_send_message(mime_message, sender: str = DOMAIN_SENDER) -> dict:
    """
    Sends a MIME email via Gmail API using the service-account JSON in env var.
    """
    service = gmail_service_for_sender(sender)

    raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")
    send_result = service.users().messages().send(
        userId="me", body={"raw": raw_message}
    ).execute()

    logging.info(f"📧 Sent email from {sender} to {mime_message['to']}, Gmail ID: {send_result['id']}")
    return send_result
