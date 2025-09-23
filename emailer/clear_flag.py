#!/usr/bin/env python3
"""
Simple script to clear the email_sent flag from a Google Drive file.
"""
import os
import sys
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def clear_email_sent_flag(file_id):
    """Clear the email_sent flag from a Google Drive file."""
    
    # Set up credentials
    creds = Credentials(
        None,
        refresh_token=os.environ.get('GMAIL_REFRESH_TOKEN'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ.get('GMAIL_SA_CLIENT_ID'),
        client_secret=os.environ.get('GMAIL_SA_CLIENT_SECRET'),
        scopes=['https://www.googleapis.com/auth/drive']
    )
    creds.refresh(Request())

    # Create Drive service
    drive = build('drive', 'v3', credentials=creds)

    # Get current appProperties
    file_metadata = drive.files().get(
        fileId=file_id,
        fields="appProperties",
        supportsAllDrives=True
    ).execute()
    
    current_props = file_metadata.get("appProperties", {}) or {}
    print(f"Current appProperties: {current_props}")
    
    # Clear the email_sent flag
    new_props = current_props.copy()
    new_props['email_sent'] = 'false'
    
    drive.files().update(
        fileId=file_id,
        body={'appProperties': new_props},
        supportsAllDrives=True,
        fields='id'
    ).execute()

    print(f'✅ Cleared email_sent flag for file: {file_id}')
    print(f'Updated appProperties: {new_props}')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 clear_flag.py <file_id>")
        sys.exit(1)
    
    file_id = sys.argv[1]
    clear_email_sent_flag(file_id)