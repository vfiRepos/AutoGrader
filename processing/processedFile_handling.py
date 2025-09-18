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
        scopes=DRIVE_SCOPES,
    )

    # Refresh immediately to get a valid access token
    logger.info("🔄 Refreshing OAuth2 credentials...")
    creds.refresh(Request())
    logger.info("✅ OAuth2 credentials refreshed successfully")
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def list_files_in_folder(folder_id: str, page_size: int = 100, service=None):
    svc = service or get_drive_service()
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

def mark_processed(file_id: str, service=None):
    """
    Mark file processed by setting appProperties. Requires write scope.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🔄 Starting mark_processed for file_id: {file_id}")
        
        svc = service or get_drive_service(use_full_scope=True)
        logger.info(f"✅ Drive service created successfully for file_id: {file_id}")
        
        now = datetime.now(timezone.utc).isoformat()
        props = {"processed": "true", "processed_at": now, "inflight": "false"}
        logger.info(f"📝 Setting appProperties for file_id {file_id}: {props}")
        
        result = svc.files().update(
            fileId=file_id, 
            body={"appProperties": props},
            supportsAllDrives=True,
            fields="id, appProperties"
        ).execute()
        
        logger.info(f"✅ Successfully marked file as processed: {file_id}")
        logger.info(f"📊 Update result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to mark file as processed: {file_id}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        logger.error(f"❌ Error message: {str(e)}")
        logger.exception("❌ Full error details:")
        raise
