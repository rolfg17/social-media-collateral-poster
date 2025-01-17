"""Google Drive integration for managing file uploads and sharing."""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class DriveManager:
    """Handles Google Drive operations including authentication and file uploads."""
    
    def __init__(self):
        """Initialize the Drive manager using environment variables."""
        self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            raise ValueError("Google credentials file not found. Set GOOGLE_CREDENTIALS_PATH in .env")
        
        self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        if not self.folder_id:
            raise ValueError("Google Drive folder ID not found. Set GOOGLE_DRIVE_FOLDER_ID in .env")
        
        self.credentials = None
        self.service = None
    
    def authenticate(self) -> bool:
        """Authenticate with Google Drive.
        
        Returns:
            bool: True if authentication was successful
        """
        try:
            # Check if we have valid credentials
            if os.path.exists('token.json'):
                self.credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            # If there are no (valid) credentials available, let the user log in.
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    self.credentials = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open('token.json', 'w') as token:
                    token.write(self.credentials.to_json())
            
            # Build the service
            self.service = build('drive', 'v3', credentials=self.credentials)
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def upload_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Upload a file to Google Drive.
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            Optional[Dict[str, Any]]: File metadata if successful, None otherwise
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return None
            
            # Add timestamp to filename
            base_name = os.path.basename(file_path)
            name_without_ext, ext = os.path.splitext(base_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{name_without_ext}_{timestamp}{ext}"
            
            file_metadata = {
                'name': new_filename,
                'parents': [self.folder_id]
            }
            
            media = MediaFileUpload(
                file_path,
                mimetype='image/jpeg',
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            logger.info(f"File uploaded: {file.get('id')}")
            return file
            
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return None
    
    def get_shareable_link(self, file_id: str) -> Optional[str]:
        """Get a shareable link for a file.
        
        Args:
            file_id: ID of the file
            
        Returns:
            Optional[str]: Shareable link if successful, None otherwise
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return None
            
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file.get('webViewLink')
            
        except Exception as e:
            logger.error(f"Failed to get shareable link: {str(e)}")
            return None
