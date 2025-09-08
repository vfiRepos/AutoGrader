import base64
import json
import google.auth
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _drive_service():
    creds, _ = google.auth.default(scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def parse_pubsub_event(event):
    """
    Decode and parse Pub/Sub event into dict.
    """
    msg = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
    return {
        "fileId": msg["fileId"],
        "fileName": msg["fileName"],
        "rep": msg.get("rep", "unknown"),
        "managerEmail": msg.get("managerEmail", "manager@yourdomain.com")
    }


def fetch_transcript_by_id(file_id: str) -> str:
    """
    Download/export a transcript file from Google Drive as plain text.
    """
    drive = _drive_service()

    try:
        # Try Google Docs export
        content = drive.files().export(
            fileId=file_id,
            mimeType="text/plain"
        ).execute()
        return content.decode("utf-8")
    except Exception:
        # Fallback for PDFs, TXT files, etc.
        request = drive.files().get_media(fileId=file_id)
        content = request.execute()
        return content.decode("utf-8")
