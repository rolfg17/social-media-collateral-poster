"""Test script for Google Drive integration."""

import os
from drive_manager import DriveManager

# Google Drive folder ID for uploads
FOLDER_ID = "1hmrwxMI6c-J32_WWeau0PQLtBxF0IUkf"

def test_drive_auth():
    """Test Google Drive authentication and file upload."""
    # Use the downloaded credentials file
    credentials_path = "client_secret_160267383749-oj19uu5hh14nqequ5bn2uuu52eq4dmj7.apps.googleusercontent.com.json"
    
    if not os.path.exists(credentials_path):
        print(f"Error: Credentials file not found at {credentials_path}")
        return False
    
    drive_manager = DriveManager(credentials_path)
    success = drive_manager.authenticate()
    
    if not success:
        print("Authentication failed!")
        return False
    
    print("Authentication successful!")
    
    # Create a small test image
    test_image_path = "test_upload.jpg"
    with open(test_image_path, "wb") as f:
        f.write(b"Test image content")
    
    try:
        # Test file upload
        print(f"Attempting to upload test file to folder: {FOLDER_ID}")
        result = drive_manager.upload_file(test_image_path, FOLDER_ID)
        
        if result:
            print(f"Upload successful!")
            print(f"File ID: {result.get('id')}")
            print(f"Web link: {result.get('webViewLink')}")
            return True
        else:
            print("Upload failed!")
            return False
            
    finally:
        # Clean up test file
        if os.path.exists(test_image_path):
            os.remove(test_image_path)

if __name__ == "__main__":
    test_drive_auth()
