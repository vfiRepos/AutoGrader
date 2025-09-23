import base64
import json
import logging
from typing import Any
import google.auth
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os

SCOPES = ["https://www.googleapis.com/auth/drive"]



def _drive_service():
    """Create Drive API client using OAuth2 credentials."""
    # Debug: Check if environment variables are present
    refresh_token = os.environ.get("REFRESH_TOKEN")
    client_id = os.environ.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET")

    
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    creds.refresh(Request())


    return build("drive", "v3", credentials=creds, cache_discovery=False)

logger = logging.getLogger(__name__)

def parse_pubsub_event(event: Any) -> dict:
    """
    Accepts many shapes:
      - dict with 'data' (base64-encoded JSON string)  -> Pub/Sub minimal
      - dict with 'message' containing 'data'         -> Pub/Sub push wrapper
      - dict with fileId/fileName directly            -> our local test payload
      - a JSON string                                 -> raw JSON body
    Returns a dict with the decoded task.
    Raises ValueError/TypeError on clearly invalid payloads.
    """
    import logging
    logger.info(f"🔎 Raw event: {event!r}")

    if isinstance(event, dict):
        if "data" in event:
            # Pub/Sub minimal format
            raw = event["data"]
            decoded = base64.b64decode(raw).decode("utf-8")
            return json.loads(decoded)
        elif "message" in event and "data" in event["message"]:
            # Pub/Sub push wrapper format (e.g., Eventarc)
            raw = event["message"]["data"]
            decoded = base64.b64decode(raw).decode("utf-8")
            return json.loads(decoded)
        elif "fileId" in event and "fileName" in event:
            # Direct test payload (already a dict)
            return event
        else:
            raise ValueError("Unsupported dictionary event format")
    elif isinstance(event, str):
        # Raw JSON string
        return json.loads(event)
    else:
        raise ValueError(f"Unsupported event type: {type(event)}")


def fetch_transcript_by_id(file_id: str) -> str:
    """
    Download/export a transcript file from Google Drive as plain text.
    Returns None if file not found or other error occurs.
    """
    logger.info(f"🔍 Attempting to fetch transcript for file_id: {file_id}")
    drive = _drive_service()

    try:
        # First, get file metadata to understand the file type
        file_metadata = drive.files().get(fileId=file_id, fields="name,mimeType").execute()
        file_name = file_metadata.get('name', 'Unknown')
        mime_type = file_metadata.get('mimeType', 'Unknown')
        logger.info(f"📄 File: {file_name}, MIME type: {mime_type}")
        
        # Try Google Docs export first
        content = drive.files().export(
            fileId=file_id,
            mimeType="text/plain"
        ).execute()
        logger.info(f"✅ Successfully exported Google Doc as text. Content length: {len(content)}")
        return content.decode("utf-8")
    except Exception as e:
        logger.warning(f"⚠️ Google Docs export failed for {file_id}: {e}")
        try:
            # Fallback for PDFs, TXT files, etc.
            logger.info(f"🔄 Trying get_media fallback for {file_id}")
            request = drive.files().get_media(fileId=file_id)
            content = request.execute()
            logger.info(f"✅ Successfully downloaded file media. Content length: {len(content)}")
            return content.decode("utf-8")
        except Exception as e2:
            logger.error(f"❌ Both export and get_media failed for {file_id}: {e2}")
            return None  # Return None to indicate failure
