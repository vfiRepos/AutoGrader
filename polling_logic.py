from google.auth import default
from googleapiclient.discovery import build

folder_id = "1DN6ACr1aVn_o1JBReCB9Uw8_cPPR7kkn"

def get_drive_service():
    creds, _ = default(scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds)

def fetch_latest_transcript(folder_id: str):
    """
    Fetch the latest transcript file (as text) from a specific Google Drive folder.
    """
    service = get_drive_service()

    # Query only inside the shared folder
    results = service.files().list(
    q=f"'{folder_id}' in parents",
    supportsAllDrives=True,
    includeItemsFromAllDrives=True,
    orderBy="createdTime desc",
    pageSize=10,
    fields="files(id, name)"
    ).execute()


    files = results.get("files", [])
    if not files:
        print("No files found.")
    else:
        for f in files:
            print(f"{f['name']} ({f['id']})")


    file_id = files[0]["id"]
    file_name = files[0]["name"]

    # Export DOCX → plain text
    request = service.files().export_media(fileId=file_id, mimeType="text/plain")
    data = request.execute()
    transcript_text = data.decode("utf-8")

    return file_name, transcript_text
