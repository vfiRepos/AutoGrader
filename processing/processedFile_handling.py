# drive_only_utils.py
from io import BytesIO
from datetime import datetime, timezone
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os

# Use readonly if you only need read (export/get_media). If you also update appProperties or move files,
# use full drive scope below
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]  # for updates / move / appProperties

def get_drive_service(use_full_scope=False):
    """Create Drive API client using OAuth2 credentials (same as pubsub_logic.py)."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Debug: Check if environment variables are present
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    client_id = os.environ.get("GMAIL_SA_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_SA_CLIENT_SECRET")
    
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
        scopes=DRIVE_SCOPES,
    )

    # Refresh immediately to get a valid access token
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def list_files_in_folder(folder_id: str, page_size: int = 100, service=None):
    svc = get_drive_service()
    q = f"'{folder_id}' in parents and trashed = false"
    resp = svc.files().list(q=q, fields="files(id, name, createdTime, mimeType)", pageSize=page_size).execute()
    return resp.get("files", [])

def fetch_text_from_file(file_id: str, service=None):
    svc = service or get_drive_service()
    # try export (Google Docs)
    try:
        content = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="ignore")
        return str(content)
    except Exception:
        # fallback to downloading media
        request = svc.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return fh.getvalue().decode("utf-8", errors="ignore")

