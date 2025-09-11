import base64
import json
import logging
from typing import Any
import google.auth
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _drive_service():
    """Create Drive service with domain-wide delegation to impersonate no-reply@vfi.net."""
    creds, _ = google.auth.default(scopes=SCOPES)
    # Try domain-wide delegation
    try:
        delegated_creds = creds.with_subject('no-reply@vfi.net')
        return build("drive", "v3", credentials=delegated_creds, cache_discovery=False)
    except Exception:
        # Fallback to default credentials if DWD fails
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
    drive = _drive_service()

    try:
        # Try Google Docs export
        content = drive.files().export(
            fileId=file_id,
            mimeType="text/plain"
        ).execute()
        return content.decode("utf-8")
    except Exception as e:
        logger.warning(f"Google Docs export failed for {file_id}: {e}")
        try:
            # Fallback for PDFs, TXT files, etc.
            request = drive.files().get_media(fileId=file_id)
            content = request.execute()
            return content.decode("utf-8")
        except Exception as e2:
            logger.error(f"File fetch failed for {file_id}: {e2}")
            return None  # Return None to indicate failure
