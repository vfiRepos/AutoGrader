def move_file_to_processed(service, file_id, processed_folder_id):
    """
    Moves a file into the Processed folder.
    Automatically detects the file's current parent(s).
    """
    # 1. Get the file's current parent(s)
    file = service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents", []))

    # 2. Move file into Processed (remove old parent(s), add new one)
    service.files().update(
        fileId=file_id,
        addParents=processed_folder_id,
        removeParents=previous_parents,
        fields="id, parents"
    ).execute()

    print(f"Moved file {file_id} to Processed folder ({processed_folder_id})")


def create_processed_folder(service, parent_folder_id):
    """Creates a 'Processed' folder inside the given parent folder."""
    file_metadata = {
        'name': 'Processed',
        'parents': [parent_folder_id],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    file = service.files().create(body=file_metadata, fields='id').execute()
    return file.get('id')


def find_and_process_all_files(service, parent_folder_id):
    """
    Finds all files in a folder, ensures a 'Processed' folder exists,
    and moves the files into it.
    """
    # 1. Get all files (non-folders) in the parent folder
    results = service.files().list(
        q=f"'{parent_folder_id}' in parents and mimeType!='application/vnd.google-apps.folder'",
        fields="files(id, name, parents)"
    ).execute()
    
    files = results.get("files", [])
    if not files:
        print("No files found in folder.")
        return
    
    print(f"Found {len(files)} files in folder.")

    # 2. Check if "Processed" folder exists, else create it
    processed_results = service.files().list(
        q=f"'{parent_folder_id}' in parents and name='Processed' and mimeType='application/vnd.google-apps.folder'",
        fields="files(id)"
    ).execute()
    
    processed_folders = processed_results.get("files", [])
    if processed_folders:
        processed_folder_id = processed_folders[0]["id"]
    else:
        processed_folder_id = create_processed_folder(service, parent_folder_id)
        print(f"Created 'Processed' folder: {processed_folder_id}")

    # 3. Loop through each file and move it
    for file in files:
        file_id = file["id"]
        move_file_to_processed(service, file_id, processed_folder_id)
        print(f"Moved {file['name']} to 'Processed' folder.")
