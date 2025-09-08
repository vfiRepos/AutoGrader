import asyncio
import os
from grading_manager import gradingManager

import asyncio
from pubsub_logic import parse_pubsub_event, fetch_transcript_by_id
from grading_manager import gradingManager
from processedFile_handling import mark_processed
import asyncio
import json
from pubsub_logic import parse_pubsub_event, fetch_transcript_by_id
from grading_manager import gradingManager
from processedFile_handling import mark_processed
from email_logic import gmail_send_message, build_email_with_attachment
from build_html import build_html_body

# Pub/Sub topic for emailer
EMAILER_TOPIC = "projects/YOUR_PROJECT_ID/topics/transcripts.processed"

import base64, json, google.auth
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def _drive_service():
    creds, _ = google.auth.default(scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def parse_pubsub_event(event):
    msg = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
    return {
        "fileId": msg["fileId"],
        "fileName": msg["fileName"],
        "rep": msg.get("rep", "unknown"),
        "managerEmail": msg.get("managerEmail", "manager@yourdomain.com")
    }

def fetch_transcript_by_id(file_id: str) -> str:
    drive = _drive_service()
    try:
        # For Google Docs
        content = drive.files().export(fileId=file_id, mimeType="text/plain").execute()
        return content.decode("utf-8")
    except Exception:
        # For TXT/PDF/others
        content = drive.files().get_media(fileId=file_id).execute()
        return content.decode("utf-8", errors="ignore")



def log_active_identity():
    creds, project = google.auth.default()
    print(f"🔎 Running as service account: {creds.service_account_email if hasattr(creds, 'service_account_email') else 'unknown'}")
    print(f"📂 Default project: {project}")

def pubsub_handler(event, context):
    """
    Cloud Function entrypoint: processes one transcript task from Pub/Sub.
    """
    log_active_identity() 
    # 1. Parse event
    task = parse_pubsub_event(event)
    file_id = task["fileId"]
    file_name = task["fileName"]
    rep = task["rep"]
    manager_email = task["managerEmail"]

    print(f"📩 Received transcript task for {file_name} (rep={rep})")

    # 2. Fetch transcript text
    transcript = fetch_transcript_by_id(file_id)
    if not transcript:
        transcript = "⚠️ No transcript content available."

    # 3. Run grading
    grader = gradingManager()
    results, synthesis_result = asyncio.run(grader.grade_all(transcript))

    # 4. Mark file processed in Drive
    mark_processed(file_id)

    html_body = build_html_body(file_name, results, synthesis_result)

    # 5. Publish results for the emailer
    # Build the email
    email_msg = build_email_with_attachment(
        to_email="gusdaskalakis@gmail.com",
        subject=f"Transcript Results: {file_name}",
        html_body=html_body,     # your grading results summary
        transcript=transcript,   # raw transcript text
        sender="manager@vfi.net" # must be Workspace account
    )

# Send the email
    gmail_send_message(email_msg, sender="no-reply@vfi.net")


    print(f"🎉 Finished {file_name}, published email task for manager {manager_email}")

    

    
