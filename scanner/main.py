import json
import base64
from datetime import datetime, timezone

import google.auth
from googleapiclient.discovery import build
from google.cloud import pubsub_v1

# Adjust these
PROJECT_ID = "YOUR_PROJECT_ID"
TOPIC = f"projects/{PROJECT_ID}/topics/transcripts.to_process"
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Map reps to their shared transcript folder IDs
REP_FOLDERS = {
    "alice": "FOLDER_ID_ALICE",
    "bob": "FOLDER_ID_BOB",
    # add more reps here
}


def _drive_service():
    """Create Drive API client using ADC (service account bound to Cloud Function/Run)."""
    creds, _ = google.auth.default(scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _pubsub_client():
    return pubsub_v1.PublisherClient()


def list_unprocessed_files(drive, folder_id):
    """Find files that aren’t marked processed or inflight."""
    query = (
        f"'{folder_id}' in parents and trashed = false "
        f"and (not appProperties has {{ key='processed' value='true' }}) "
        f"and (not appProperties has {{ key='inflight' value='true' }})"
    )
    fields = "files(id, name, mimeType, appProperties)"
    resp = drive.files().list(q=query, fields=fields).execute()
    return resp.get("files", [])


def mark_inflight(drive, file_id):
    """Set inflight=true so we don’t double-publish this file."""
    now = datetime.now(timezone.utc).isoformat()
    body = {"appProperties": {"inflight": "true", "inflight_at": now}}
    drive.files().update(fileId=file_id, body=body).execute()


def publish_task(pub, payload: dict):
    """Send message to Pub/Sub for processor."""
    data = json.dumps(payload).encode("utf-8")
    future = pub.publish(TOPIC, data=data)
    future.result()


def http_handler(request):
    """Entry point for Cloud Function (HTTP-triggered)."""
    drive = _drive_service()
    pub = _pubsub_client()

    for rep, folder_id in REP_FOLDERS.items():
        files = list_unprocessed_files(drive, folder_id)
        for f in files:
            mark_inflight(drive, f["id"])
            publish_task(pub, {
                "fileId": f["id"],
                "fileName": f["name"],
                "mimeType": f["mimeType"],
                "rep": rep,
                "folderId": folder_id
            })

    return "Scan complete", 200
