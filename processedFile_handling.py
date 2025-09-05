from googleapiclient.discovery import build
from google.auth import default

# --- Helpers from before ---
def move_file_to_processed(service, file_id, processed_folder_id):
    """Moves a file into the Processed folder, removing old parents."""
    file = service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents", []))

    service.files().update(
        fileId=file_id,
        addParents=processed_folder_id,
        removeParents=previous_parents,
        fields="id, parents"
    ).execute()

    print(f"✅ Moved file {file_id} to Processed ({processed_folder_id})")


def create_processed_folder(service, parent_folder_id):
    """Creates a 'Processed' folder inside the given parent folder if missing."""
    file_metadata = {
        'name': 'Processed',
        'parents': [parent_folder_id],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    file = service.files().create(body=file_metadata, fields='id').execute()
    return file.get('id')


def get_drive_service():
    """Authenticate and return Google Drive service client."""
    creds, _ = default(scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds)


def fetch_latest_file(service, parent_folder_id):
    """Get the most recent file in the folder (excluding subfolders)."""
    results = service.files().list(
        q=f"'{parent_folder_id}' in parents and mimeType!='application/vnd.google-apps.folder'",
        orderBy="createdTime desc",
        pageSize=1,
        fields="files(id, name, createdTime)"
    ).execute()
    return results.get("files", [])


def ensure_processed_folder(service, parent_folder_id):
    """Check for a 'Processed' folder inside parent, create if missing."""
    processed_results = service.files().list(
        q=f"'{parent_folder_id}' in parents and name='Processed' and mimeType='application/vnd.google-apps.folder'",
        fields="files(id)"
    ).execute()

    processed_folders = processed_results.get("files", [])
    if processed_folders:
        return processed_folders[0]["id"]
    else:
        processed_folder_id = create_processed_folder(service, parent_folder_id)
        print(f"📂 Created 'Processed' folder: {processed_folder_id}")
        return processed_folder_id

def postprocess_latest_file(parent_folder_id: str):
    """
    After grading is complete, move the latest transcript
    into the 'Processed' folder inside the same parent folder.
    """
    service = get_drive_service()

    # 1. Fetch the latest file in the parent folder
    latest_files = fetch_latest_file(service, parent_folder_id)
    if not latest_files:
        print("⚠️ No files found in parent folder.")
        return

    latest_file = latest_files[0]
    file_id, file_name = latest_file["id"], latest_file["name"]
    print(f"📄 Latest file: {file_name} ({file_id})")

    # 2. Ensure Processed folder exists
    processed_folder_id = ensure_processed_folder(service, parent_folder_id)
    print(f"📂 Using Processed folder: {processed_folder_id}")

    # 3. Look up current parents of the file
    file_metadata = service.files().get(fileId=file_id, fields="parents").execute()
    current_parents = ",".join(file_metadata.get("parents", []))
    print(f"🔎 Current parents: {current_parents}")

    # 4. Move the file
    updated_file = service.files().update(
        fileId=file_id,
        addParents=processed_folder_id,
        removeParents=current_parents,
        fields="id, parents"
    ).execute()

    print(f"✅ {file_name} moved into 'Processed' (new parents: {updated_file.get('parents')})")
