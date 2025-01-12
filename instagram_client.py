import requests
import json
import logging
import uuid

logger = logging.getLogger(__name__)

class InstagramClient:
    def __init__(self, config):
        self.access_token = config['instagram'].get('access_token', '')
        self.instagram_account_id = config['instagram'].get('instagram_account_id', '')
        self.facebook_page_id = config['instagram'].get('facebook_page_id', '')
        self.test_mode = config['instagram'].get('test_mode', True)
        self.mock_mode = not (self.access_token and self.instagram_account_id and self.facebook_page_id)
        
        if self.mock_mode:
            logger.info("Running in mock mode (no Instagram credentials provided)")
        
        self.api_version = 'v18.0'
        self.base_url = f'https://graph.facebook.com/{self.api_version}'
        
    def create_container(self, image_path, caption):
        """Create a media container in draft mode"""
        if self.mock_mode:
            # Simulate API response in mock mode
            mock_id = str(uuid.uuid4())
            logger.info(f"Mock mode: Would create container with caption: {caption}")
            logger.info(f"Mock mode: Would upload image: {image_path}")
            return mock_id
            
        try:
            # First, upload the image to Facebook
            with open(image_path, 'rb') as image_file:
                url = f'{self.base_url}/{self.instagram_account_id}/media'
                
                params = {
                    'access_token': self.access_token,
                    'caption': caption,
                    'is_carousel_item': False,
                }
                
                if self.test_mode:
                    params.update({
                        'published': False,
                        'debug': 'all',
                    })
                
                files = {
                    'image_url': image_file
                }
                
                response = requests.post(url, params=params, files=files)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Created container: {result}")
                
                if self.test_mode:
                    logger.info("Test mode: Container created but not published")
                    logger.info(f"Debug info: {result.get('debug_info', {})}")
                
                return result.get('id')
                
        except Exception as e:
            logger.error(f"Error creating container: {str(e)}")
            return None
            
    def publish_container(self, container_id):
        """Publish a container (only if not in test mode)"""
        if self.mock_mode:
            logger.info(f"Mock mode: Would publish container {container_id}")
            return True
            
        if self.test_mode:
            logger.info(f"Test mode: Would publish container {container_id}")
            return True
            
        try:
            url = f'{self.base_url}/{self.instagram_account_id}/media_publish'
            
            params = {
                'access_token': self.access_token,
                'creation_id': container_id
            }
            
            response = requests.post(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Published container: {result}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing container: {str(e)}")
            return False
