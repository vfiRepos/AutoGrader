import json
import time
from datetime import datetime, timezone

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import pubsub_v1

# Adjust these
PROJECT_ID = "sales-transcript-grader"
TOPIC = f"projects/{PROJECT_ID}/topics/process_new_files"
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Map reps to their shared transcript folder IDs
REP_FOLDERS = {
    "shared_folder": "1JqJwiN37EaUe7v5_YSjBnebSds1bxV3y"
}

def _drive_service():
    """Create Drive API client with domain-wide delegation to impersonate no-reply@vfi.net."""
    creds, _ = google.auth.default(scopes=SCOPES)
    # Try domain-wide delegation
    try:
        delegated_creds = creds.with_subject('no-reply@vfi.net')
        return build("drive", "v3", credentials=delegated_creds, cache_discovery=False)
    except Exception:
        # Fallback to default credentials if DWD fails
        return build("drive", "v3", credentials=creds, cache_discovery=False)

def _pubsub_client():
    return pubsub_v1.PublisherClient()

def _with_retries(fn, *args, **kwargs):
    """Basic retry for transient Drive/PubSub errors."""
    max_attempts = 5
    backoff = 1.0
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except HttpError as e:
            # Retry 429 and 5xx
            if e.resp.status in (429, 500, 502, 503, 504):
                time.sleep(backoff)
                backoff = min(backoff * 2, 16)
                continue
            raise
        except Exception:
            # Retry common transient errors
            if attempt < max_attempts - 1:
                time.sleep(backoff)
                backoff = min(backoff * 2, 16)
                continue
            raise

import logging

def list_unprocessed_files(drive, folder_id):
    """Find files that aren't marked processed or inflight."""
    query = (
        f"'{folder_id}' in parents and trashed = false "
        f"and mimeType = 'application/vnd.google-apps.document'"
    )
    fields = "files(id, name, mimeType, appProperties)"
    resp = drive.files().list(q=query, fields=fields).execute()

    # Filter out processed/inflight files in Python
    files = resp.get("files", [])
    unprocessed = []
    for f in files:
        props = f.get("appProperties", {}) or {}
        if props.get("processed") != "true" and props.get("inflight") != "true":
            unprocessed.append(f)
    return unprocessed


def mark_inflight(drive, file_id):
    """Set inflight=true so we don’t double-publish this file."""
    now = datetime.now(timezone.utc).isoformat()
    body = {"appProperties": {"inflight": "true", "inflight_at": now}}
    _with_retries(
        drive.files().update,
        fileId=file_id,
        body=body,
        supportsAllDrives=True,
        fields="id, appProperties",
    ).execute()

def publish_task(pub, payload: dict):
    """Send message to Pub/Sub for processor."""
    data = json.dumps(payload).encode("utf-8")
    future = pub.publish(TOPIC, data=data)
    # Waiting ensures the publish truly succeeded before returning
    future.result()

def http_handler(request):
    """Entry point for Cloud Function (HTTP-triggered)."""
    drive = _drive_service()
    pub = _pubsub_client()

    total_published = 0
    for rep, folder_id in REP_FOLDERS.items():
        logging.info(f"Scanning rep={rep}, folder={folder_id}")
        files = list_unprocessed_files(drive, folder_id)
        logging.info(f"Found {len(files)} unprocessed files for rep={rep}")

        for f in files:
            logging.info(f"Processing file: {f['name']} (ID: {f['id'][:10]})")
            mark_inflight(drive, f["id"])
            publish_task(pub, {
                "fileId": f["id"],
                "fileName": f["name"],
                "mimeType": f["mimeType"],
                "rep": rep,
                "folderId": folder_id
            })
            total_published += 1

    logging.info(f"Scan complete. Published {total_published} task(s).")
    return f"Scan complete. Published {total_published} task(s).", 200
