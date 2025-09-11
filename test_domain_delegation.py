#!/usr/bin/env python3
"""
Test script to verify domain-wide delegation for mailer-sa service account.
This will test if the scanner can access files shared with no-reply@vfi.net.
"""

import json
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.cloud import secretmanager
import google.auth.transport.requests

SCOPES = ["https://www.googleapis.com/auth/drive"]

def test_domain_delegation():
    """Test if domain-wide delegation is working."""
    print("🔍 Testing Domain-Wide Delegation")
    print("=" * 50)

    try:
        # Step 1: Load service account credentials from Secret Manager
        print("📥 Loading service account credentials from Secret Manager...")
        client = secretmanager.SecretManagerServiceClient()

        name = client.secret_version_path(
            "sales-transcript-grader",  # project_id
            "gmail-sa-key",            # secret_id
            "2"                        # version_id
        )

        response = client.access_secret_version(request={"name": name})
        sa_key_json = response.payload.data.decode("UTF-8")
        print("✅ Successfully loaded credentials from Secret Manager")

        # Step 2: Create credentials and impersonate no-reply@vfi.net
        print("🎭 Creating credentials and impersonating no-reply@vfi.net...")
        creds = service_account.Credentials.from_service_account_info(
            json.loads(sa_key_json),
            scopes=SCOPES
        )

        # Impersonate no-reply@vfi.net
        delegated_creds = creds.with_subject('no-reply@vfi.net')
        print("✅ Successfully created delegated credentials")

        # Step 3: Test Google Drive access
        print("📁 Testing Google Drive access...")
        drive = build("drive", "v3", credentials=delegated_creds)

        # Try to list files (this should work if delegation is set up)
        results = drive.files().list(
            pageSize=10,
            fields="files(id, name, owners, shared)",
            q="sharedWithMe = true"  # Only files shared with the impersonated user
        ).execute()

        files = results.get('files', [])

        print("✅ Google Drive API access successful!")
        print(f"📊 Found {len(files)} shared files:")

        for file in files[:5]:  # Show first 5 files
            owners = file.get('owners', [])
            owner_emails = [owner.get('emailAddress', 'Unknown') for owner in owners]
            print(f"  • {file['name']} (ID: {file['id'][:10]}...) - Shared by: {', '.join(owner_emails)}")

        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more files")

        # Step 4: Test specific folder access (if you have a test folder)
        test_folder_id = input("\n🔍 Enter a Google Drive folder ID to test specific access (or press Enter to skip): ").strip()

        if test_folder_id:
            print(f"📂 Testing access to folder: {test_folder_id}")
            try:
                folder_results = drive.files().list(
                    q=f"'{test_folder_id}' in parents and trashed = false",
                    fields="files(id, name, mimeType)",
                    pageSize=5
                ).execute()

                folder_files = folder_results.get('files', [])
                print(f"✅ Successfully accessed folder! Found {len(folder_files)} files:")
                for file in folder_files:
                    print(f"  • {file['name']} ({file['mimeType']})")

            except Exception as e:
                print(f"❌ Could not access the folder: {e}")

        print("\n🎉 SUCCESS: Domain-wide delegation is working!")
        print("The scanner should be able to see files shared with no-reply@vfi.net")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n🔧 Troubleshooting:")

        if "secretmanager" in str(e).lower():
            print("  • Secret Manager access issue - check IAM permissions")
        elif "unauthorized" in str(e).lower():
            print("  • Domain-wide delegation not configured properly")
            print("  • Check Google Workspace admin console")
        elif "invalid_grant" in str(e).lower():
            print("  • Service account credentials invalid")
            print("  • Check Secret Manager secret version")
        else:
            print(f"  • Unexpected error: {e}")

        return False

if __name__ == "__main__":
    success = test_domain_delegation()
    exit(0 if success else 1)