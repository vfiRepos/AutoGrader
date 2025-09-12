import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import pubsub_v1

# --- OAuth2 secrets injected via --set-secrets ---
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
PROJECT_ID = os.environ["PROJECT_ID"]

# --- Drive API Scopes ---
SCOPES = ["https://www.googleapis.com/auth/drive"]

# --- Pub/Sub Configuration ---
TASK_PUB_SUB_TOPIC_ID = "process_newTranscripts"
TASK_PUB_SUB_TOPIC_PATH = f"projects/{PROJECT_ID}/topics/{TASK_PUB_SUB_TOPIC_ID}"

# --- Folder Configuration ---
REP_FOLDERS = {
    "shared_folder": "1JqJwiN37EaUe7v5_YSjBnebSds1bxV3y",
}

# --- Pub/Sub Publisher Client (initialized once) ---
_pubsub_publisher_client = pubsub_v1.PublisherClient()


def _drive_service_refresh_token():
    """Create Drive API client using secrets injected as environment variables."""
    refresh_token = REFRESH_TOKEN.strip()
    client_id = CLIENT_ID.strip()
    client_secret = CLIENT_SECRET.strip()

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    return build("drive", "v3", credentials=creds)

    
def _pubsub_client():
    """Returns a Pub/Sub publisher client."""
    # In a real scenario, you might want to pass this client around
    # or ensure it's initialized only once globally.
    return _pubsub_publisher_client


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


def mark_inflight(drive_service, file_id):
    """
    Placeholder function: In a real scenario, this would update a file's metadata
    or move it to an "in-progress" folder to avoid reprocessing.
    """
    print(f"Simulating marking file {file_id} as in-flight...")


def publish_task(pubsub_client, task_data):
    """Publishes a task message to the Pub/Sub topic."""
    data_bytes = json.dumps(task_data).encode("utf-8")
    future = pubsub_client.publish(TASK_PUB_SUB_TOPIC_PATH, data_bytes)
    print(f"Published task for file {task_data['fileId']} with message ID: {future.result()}")


def http_handler(request):
    """Entry point for Cloud Function (HTTP-triggered)."""
    # Initialize Drive service using the refresh token method
    drive = _drive_service_refresh_token()
    # Get Pub/Sub client
    pub = _pubsub_client()

    print(f"Scanner started. REP_FOLDERS has {len(REP_FOLDERS)} entries")
    total_published = 0
    for rep, folder_id in REP_FOLDERS.items():
        print(f"Scanning rep={rep}, folder={folder_id}")
        files = list_unprocessed_files(drive, folder_id) # Pass the authenticated drive service
        print(f"Found {len(files)} unprocessed files for rep={rep}")

        for f in files:
            print(f"Processing file: {f['name']} (ID: {f['id'][:10]})")
            mark_inflight(drive, f["id"]) # Pass the authenticated drive service
            publish_task(pub, {
                "fileId": f["id"],
                "fileName": f["name"],
                "mimeType": f["mimeType"],
                "rep": rep,
                "folderId": folder_id
            })
            total_published += 1

    print(f"Scan complete. Published {total_published} task(s).")
    return f"Scan complete. Published {total_published} task(s).", 200

