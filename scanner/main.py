import json
import os
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import pubsub_v1


# --- OAuth2 secrets injected via --set-secrets ---
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]  # Mounted as CLIENT_SECRET
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
    "shared_folder_2": "17zU0G6cpY60GlcCYRXVgQRozACXXGfj2", 
    "shared_folder_3": "13IgGftk0Oh3ywSjepWOANplSJO9pxrZq"
}

# --- Pub/Sub Publisher Client (initialized once) ---
_pubsub_publisher_client = pubsub_v1.PublisherClient()

def _pubsub_client():
    """Get the Pub/Sub publisher client."""
    return _pubsub_publisher_client


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


# def list_unprocessed_files(drive, folder_id):
#     """Find files that aren't marked processed or inflight."""
#     query = (
#         f"'{folder_id}' in parents and trashed = false "
#         f"and mimeType = 'application/vnd.google-apps.document'"
#     )
#     fields = "files(id, name, mimeType, appProperties)"
#     resp = drive.files().list(q=query, fields=fields).execute()

#     # Filter out processed/inflight files in Python
#     files = resp.get("files", [])
#     unprocessed = []
#     for f in files:
#         props = f.get("appProperties", {}) or {}
#         if props.get("processed") != "true" and props.get("inflight") != "true":
#             unprocessed.append(f)
#     return unprocessed


def list_files(drive, folder_id):
    query = f"'{folder_id}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.document'"
    fields = "files(id, name, mimeType, appProperties)"
    resp = drive.files().list(q=query, fields=fields).execute()
    return resp.get("files", [])

def publish_task(pubsub_client, task_data):
    """Publishes a task message to the Pub/Sub topic."""
    data_bytes = json.dumps(task_data).encode("utf-8")
    future = pubsub_client.publish(TASK_PUB_SUB_TOPIC_PATH, data_bytes)
    print(f"Published task for file {task_data['fileId']} with message ID: {future.result()}")
    return 1; 




def http_handler(request):

    """Entry point for Cloud Function (HTTP-triggered)."""
    # Initialize Drive service using the refresh token method
    drive = _drive_service_refresh_token()
    # Get Pub/Sub client
    pub = _pubsub_client()

    print(f"Scanner started. REP_FOLDERS has {len(REP_FOLDERS)} entries")
    total_published = 0  # Initialize counter for total tasks published
    
    for rep, folder_id in REP_FOLDERS.items():
        print(f"Scanning rep={rep}, folder={folder_id}")

        files = list_files(drive, folder_id); 

        print(f"Found {len(files)} files")

        for f in files:
            print(f"Processing file: {f['name']} (ID: {f['id'][:10]})")

            # Only publish if marking as inflight succeeds
            publish_task(pub, {
                "fileId": f["id"],
                "fileName": f["name"],
                "mimeType": f["mimeType"],
                "rep": rep,
                "folderId": folder_id
            })
            total_published += 1  # Increment counter for each published task


    print(f"Scan complete. Published {total_published} task(s)."); 
    return f"Scan complete. Tasks published {total_published}.", 200


