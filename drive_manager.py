"""Google Drive integration for managing file uploads and sharing."""

import os
import logging
from typing import Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class DriveManager:
    """Handles Google Drive operations including authentication and file uploads."""
    
    def __init__(self, credentials_path: str):
        """Initialize the Drive manager.
        
        Args:
            credentials_path: Path to the credentials.json file
        """
        self.credentials_path = credentials_path
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
    
    def upload_file(self, file_path: str, folder_id: str) -> Optional[Dict[str, Any]]:
        """Upload a file to Google Drive.
        
        Args:
            file_path: Path to the file to upload
            folder_id: ID of the folder to upload to
            
        Returns:
            Optional[Dict[str, Any]]: File metadata if successful, None otherwise
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return None
            
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [folder_id]
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
