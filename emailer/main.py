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
logger = logging.getLogger(__name__)

# Gmail service account configuration
GMAIL_SA_ENVVAR = "GMAIL_SA_KEY"
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
DOMAIN_SENDER = os.environ.get("FROM_EMAIL", "no-reply@vfi.net")

# Email recipient configuration
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "sales-team@vfi.net")

def _load_sa_credentials(scopes=GMAIL_SCOPES):
    """Load service account info from environment variable or file."""
    # First try environment variable (for direct JSON content)
    raw = os.environ.get(GMAIL_SA_ENVVAR)
    if raw:
        sa_info = json.loads(raw)
    else:
        # Try to read from file path (for secrets mounted as files)
        secret_path = os.environ.get("GMAIL_SA_KEY_PATH", "/secrets/gmail-sa-key.json")
        try:
            with open(secret_path, 'r') as f:
                sa_info = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Service account credentials not found. Tried env var {GMAIL_SA_ENVVAR} and file {secret_path}: {e}")

    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
    return creds

def gmail_service_for_sender(sender: str):
    """Return a gmail API client that impersonates the sender."""
    creds = _load_sa_credentials()
    delegated = creds.with_subject(sender)
    return build("gmail", "v1", credentials=delegated, cache_discovery=False)

def format_grading_html(payload):
    """Format grading results as HTML for email body."""
    results = payload['grading_results']
    file_name = payload['fileName']
    rep = payload['rep']

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
            .skill-card {{ background: #ecf0f1; margin: 10px 0; padding: 15px; border-radius: 5px; }}
            .grade {{ font-size: 24px; font-weight: bold; }}
            .grade-A {{ color: #27ae60; }}
            .grade-B {{ color: #f39c12; }}
            .grade-C {{ color: #e67e22; }}
            .grade-D {{ color: #e74c3c; }}
            .grade-F {{ color: #c0392b; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Sales Transcript Grading Results</h1>
            <p><strong>File:</strong> {file_name}</p>
            <p><strong>Representative:</strong> {rep}</p>
        </div>

        <h2>Individual Skill Assessments</h2>
    """

    # Add individual skill results
    for skill_name, skill_data in results['individual_scores'].items():
        grade = skill_data['grade']
        reasoning = skill_data['reasoning']
        grade_class = f"grade-{grade}"

        html += f"""
        <div class="skill-card">
            <h3>{skill_name.replace('_', ' ').title()}</h3>
            <div class="grade {grade_class}">{grade}</div>
            <p>{reasoning}</p>
        </div>
        """

    # Add final synthesis
    synthesis = results['final_synthesis']
    synthesis_grade = synthesis['grade']
    synthesis_reasoning = synthesis['reasoning']
    synthesis_class = f"grade-{synthesis_grade}"

    html += f"""
        <h2>🎯 Final Synthesis</h2>
        <div class="skill-card">
            <h3>Overall Performance</h3>
            <div class="grade {synthesis_class}">{synthesis_grade}</div>
            <p>{synthesis_reasoning}</p>
        </div>

        <p><em>The full transcript is attached to this email.</em></p>
    </body>
    </html>
    """

    return html

def build_email_with_attachment(to_email, subject, html_body, transcript_text, file_name, sender):
    """Build email with HTML body and transcript attachment."""
    message = MIMEMultipart()
    message["to"] = to_email
    message["from"] = sender
    message["subject"] = subject

    # HTML part
    message.attach(MIMEText(html_body, "html"))

    # Transcript as attachment
    attachment = MIMEBase("text", "plain")
    attachment.set_payload(transcript_text.encode("utf-8"))
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename=f"{file_name}_transcript.txt")
    message.attach(attachment)

    return message

def send_grading_email(payload):
    """Send grading results email with transcript attachment."""
    try:
        # Extract data from payload
        grading_results = payload['grading_results']
        file_name = payload['fileName']
        rep = payload['rep']
        transcript = payload['transcript']

        logger.info(f"📧 Preparing email for {file_name} (rep: {rep})")

        # Use the configured recipient email
        to_email = RECIPIENT_EMAIL
        logger.info(f"📧 Sending to: {to_email}")
        logger.info(f"📧 From: {DOMAIN_SENDER}")

        # Create email content
        subject = f"Sales Transcript Grading: {file_name} - {rep}"
        logger.info(f"📧 Subject: {subject}")

        logger.info("📧 Generating HTML body...")
        html_body = format_grading_html(payload)

        logger.info("📧 Building email with transcript attachment...")
        email_message = build_email_with_attachment(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            transcript_text=transcript,
            file_name=file_name,
            sender=DOMAIN_SENDER
        )

        logger.info("📧 Creating Gmail service...")
        service = gmail_service_for_sender(DOMAIN_SENDER)

        logger.info("📧 Encoding email message...")
        raw_message = base64.urlsafe_b64encode(email_message.as_bytes()).decode("utf-8")

        logger.info("📧 Sending email via Gmail API...")
        send_result = service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()

        logger.info(f"✅ EMAIL SUCCESSFULLY SENT!")
        logger.info(f"✅ To: {to_email}")
        logger.info(f"✅ File: {file_name}")
        logger.info(f"✅ Gmail Message ID: {send_result['id']}")
        return send_result

    except Exception as e:
        logger.exception(f"❌ EMAIL SENDING FAILED for {payload.get('fileName', 'unknown')}: {e}")
        logger.error("❌ Gmail API call failed")
        raise

def email_handler(event, context):
    """
    Cloud Function entry point for processing grading email requests.
    Triggered by Pub/Sub messages from the transcript processor.
    """
    try:
        logger.info("📨 EMAIL HANDLER TRIGGERED!")

        # Parse Pub/Sub message
        if 'data' in event:
            payload = json.loads(base64.b64decode(event['data']).decode('utf-8'))
            logger.info("📨 Received Pub/Sub message from processor")
        else:
            payload = event  # For direct testing
            logger.info("📨 Received direct test payload")

        file_name = payload.get('fileName', 'unknown')
        logger.info(f"📧 Processing email request for: {file_name}")
        logger.info(f"📧 Rep: {payload.get('rep', 'unknown')}")
        logger.info(f"📧 Recipient will be: {RECIPIENT_EMAIL}")

        # Send the grading email
        logger.info("📧 Calling send_grading_email()...")
        result = send_grading_email(payload)
        logger.info("✅ EMAIL SENT SUCCESSFULLY!")
        logger.info(f"✅ Gmail Message ID: {result['id']}")

        return {
            "status": "success",
            "email_id": result['id'],
            "recipient": RECIPIENT_EMAIL,
            "file_processed": file_name
        }

    except Exception as e:
        logger.exception("❌ EMAIL HANDLER FAILED")
        logger.error("❌ Email was NOT sent due to error")
        return {
            "status": "error",
            "error": str(e)
        }
