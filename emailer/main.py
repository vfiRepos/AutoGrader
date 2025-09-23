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
from google.oauth2.credentials import Credentials
import sys


logging.basicConfig(
    level=logging.DEBUG,       # show all levels
    stream=sys.stdout,         # make sure logs go to stdout
    force=True                 # override any previous settings
)
logger = logging.getLogger(__name__)

# Gmail OAuth configuration (set via Cloud Function secrets)
GMAIL_SA_CLIENT_ID = os.environ.get("GMAIL_SA_CLIENT_ID")
GMAIL_SA_CLIENT_SECRET = os.environ.get("GMAIL_SA_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Sender/recipient defaults
DOMAIN_SENDER = os.environ.get("FROM_EMAIL", "gdaskalakis@vfi.net")
RECIPIENT_EMAIL = os.environ.get("managerEmail", "gusdaskalakis@gmail.com")

# No cache needed - we'll use Google Drive file metadata


def gmail_service():
    """Return a Gmail API client using OAuth client + refresh token."""
    creds = Credentials(
        None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_SA_CLIENT_ID,
        client_secret=GMAIL_SA_CLIENT_SECRET,
        scopes=GMAIL_SCOPES,
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def drive_service():
    """Return a Drive API client using OAuth client + refresh token."""
    creds = Credentials(
        None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_SA_CLIENT_ID,
        client_secret=GMAIL_SA_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)




def normalize_grade_class(grade: str) -> str:
    """Normalize grade strings into safe CSS class suffixes."""
    if not grade:
        return "grade-NA"
    g = grade.upper().strip()

    # Handle common variants
    if g.startswith("A"):
        return "grade-A"
    elif g.startswith("B"):
        return "grade-B"
    elif g.startswith("C"):
        return "grade-C"
    elif g.startswith("D"):
        return "grade-D"
    elif g.startswith("F"):
        return "grade-F"
    else:
        return "grade-NA"

def format_grading_html(payload, timestamp):
    """Format grading results as HTML for email body."""
    logger.info(f"🔍 DEBUG: Formatting grading HTML for payload keys: {list(payload.keys())}")
    results = payload['grading_results']
    logger.info(f"🔍 DEBUG: grading_results keys: {list(results.keys())}")
    logger.info(f"🔍 DEBUG: individual_scores type: {type(results.get('individual_scores', 'MISSING'))}")
    logger.info(f"🔍 DEBUG: final_synthesis type: {type(results.get('final_synthesis', 'MISSING'))}")
    
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
            <p><strong>Email ID:</strong> {timestamp}</p>
        </div>

        <h2>Individual Skill Assessments</h2>
    """

    # Add individual skill results
    for skill_name, skill_data in results['individual_scores'].items():
        grade = skill_data['grade']
        reasoning = skill_data['reasoning']
        grade_class = normalize_grade_class(grade)


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
    synthesis_class = normalize_grade_class(synthesis_grade)

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
    safe_name = file_name.replace(" ", "_").replace("/", "_")
    attachment.add_header("Content-Disposition", "attachment", filename=f"{safe_name}_transcript.txt")
    message.attach(attachment)

    return message
def send_grading_email(payload):
    """Send grading results email with transcript attachment."""


    file_name = payload['fileName']
    rep = payload['rep']
    transcript = payload['transcript']

 
    to_email = RECIPIENT_EMAIL


    # Create email subject + body with unique timestamp
    import time
    timestamp = int(time.time() * 1000)  # milliseconds
    subject = f"Sales Transcript Grading: {file_name} - {rep} [{timestamp}]"


    html_body = format_grading_html(payload, timestamp)

    email_message = build_email_with_attachment(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        transcript_text=transcript,
        file_name=file_name,
        sender=DOMAIN_SENDER
    )

    # Encode properly for Gmail API
    raw_message = base64.urlsafe_b64encode(email_message.as_bytes()).decode("utf-8")

    logger.info("📧 Creating Gmail service...")
    service = gmail_service()

    logger.info("📧 Sending email via Gmail API...")
    send_result = service.users().messages().send(
        userId="me",
        body={"raw": raw_message}
    ).execute()


    return send_result



def email_handler(event, context):
    # Parse Pub/Sub message
    decoded = base64.b64decode(event["data"]).decode("utf-8")
    if not decoded.strip():
        raise ValueError("Empty Pub/Sub message")
    payload = json.loads(decoded)
    
    file_id = payload.get('fileId')
    file_name = payload.get('fileName', 'unknown')
    transcript = payload.get('transcript', '')
    
    # Check if transcript is missing or empty
    if not transcript or not transcript.strip():
        logger.warning(f"⚠️ No transcript available for file {file_id} ({file_name}), skipping email")
        return {"status": "skipped", "reason": "no_transcript"}
    
    # Check if email already sent for this file
    try:
        drive = drive_service()
        file_metadata = drive.files().get(
            fileId=file_id,
            fields="appProperties",
            supportsAllDrives=True
        ).execute()
        
        app_props = file_metadata.get('appProperties', {})
        if app_props.get('email_sent') == 'true':
            logger.info(f"📧 Email already sent for file {file_id}, skipping")
            return {"status": "skipped", "reason": "already_sent"}
    except Exception as e:
        logger.warning(f"⚠️ Could not check email status for {file_id}: {e}")
    
    # Send the email
    result = send_grading_email(payload)
    
    # Mark as email sent
    try:
        drive.files().update(
            fileId=file_id,
            body={'appProperties': {'email_sent': 'true'}},
            supportsAllDrives=True
        ).execute()
        logger.info(f"✅ Marked file {file_id} as email sent")
    except Exception as e:
        logger.warning(f"⚠️ Could not mark email sent for {file_id}: {e}")
    
    return result
    
