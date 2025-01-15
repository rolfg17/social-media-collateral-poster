"""Test script for Google Drive integration."""

import os
from drive_manager import DriveManager

# Google Drive folder ID for uploads
FOLDER_ID = os.getenv("FOLDER_ID", "1hmrwxMI6c-J32_WWeau0PQLtBxF0IUkf")

def test_drive_auth():
    """Test Google Drive authentication and file upload."""
    try:
        drive_manager = DriveManager()
    except ValueError as e:
        print(f"Setup error: {str(e)}")
        return False
    
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
        print("Attempting to upload test file...")
        result = drive_manager.upload_file(test_image_path)
        
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
