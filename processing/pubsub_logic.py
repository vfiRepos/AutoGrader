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
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    client_id = os.environ.get("GMAIL_SA_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_SA_CLIENT_SECRET")
    
    logger.info(f"🔍 OAuth2 Debug - refresh_token present: {bool(refresh_token)}")
    logger.info(f"🔍 OAuth2 Debug - client_id present: {bool(client_id)}")
    logger.info(f"🔍 OAuth2 Debug - client_secret present: {bool(client_secret)}")
    
    if not refresh_token:
        logger.error("❌ GMAIL_REFRESH_TOKEN is missing or empty")
        raise ValueError("GMAIL_REFRESH_TOKEN environment variable is required")
    if not client_id:
        logger.error("❌ GMAIL_SA_CLIENT_ID is missing or empty")
        raise ValueError("GMAIL_SA_CLIENT_ID environment variable is required")
    if not client_secret:
        logger.error("❌ GMAIL_SA_CLIENT_SECRET is missing or empty")
        raise ValueError("GMAIL_SA_CLIENT_SECRET environment variable is required")
    
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    # Refresh immediately to get a valid access token
    logger.info("🔄 Refreshing OAuth2 credentials...")
    creds.refresh(Request())
    logger.info("✅ Successfully authenticated with OAuth2 credentials")

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
    try:
        # If functions-framework gave us a flask request body already parsed as dict
        if isinstance(event, dict):
            # Pub/Sub minimal: {"data":"<base64...>"}
            if "data" in event and isinstance(event["data"], str):
                raw = event["data"]
                # sometimes it's base64 encoded
                try:
                    decoded = base64.b64decode(raw).decode("utf-8")
                    return json.loads(decoded)
                except Exception:
                    # maybe it's plain json string
                    try:
                        return json.loads(raw)
                    except Exception:
                        raise ValueError("Unable to decode 'data' field in event")

            # Pub/Sub wrapper: {"message": {"data": "..."}}
            if "message" in event and isinstance(event["message"], dict):
                msg = event["message"]
                if "data" in msg and isinstance(msg["data"], str):
                    try:
                        decoded = base64.b64decode(msg["data"]).decode("utf-8")
                        return json.loads(decoded)
                    except Exception:
                        try:
                            return json.loads(msg["data"])
                        except Exception:
                            raise ValueError("Unable to decode message.data")

            # Already a plain task dict: {"fileId":"123", ...}
            if "fileId" in event and "fileName" in event:
                return event

            # if it's empty dict, bail
            if not event:
                raise ValueError("Empty dict body for event.")

        # If event is a raw string body
        if isinstance(event, str):
            if not event.strip():
                raise ValueError("Empty string body for event.")
            # try parse as JSON
            return json.loads(event)

        # fallback: unsupported type
        raise TypeError(f"Unsupported event type: {type(event)}")

    except Exception as e:
        logger.error(f"Failed to parse Pub/Sub event: {e}")
        raise



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
