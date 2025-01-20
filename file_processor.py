"""File processing utilities for Social Media Collateral Poster."""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file processing and content extraction."""
    
    def __init__(self, text_processor):
        """Initialize the file processor.
        
        Args:
            text_processor: TextProcessor instance for content processing
        """
        self.text_processor = text_processor
    
    def process_file(self, file) -> Optional[Dict[str, Dict[str, str]]]:
        """Process an uploaded file and extract sections.
        
        Args:
            file: The uploaded file object
            
        Returns:
            Dictionary with 'sections' and 'cleaned_contents' if successful, None otherwise
        """
        try:
            content = file.read().decode('utf-8')
            file.seek(0)  # Reset file pointer
            
            # Process the content
            sections = self.text_processor.parse_markdown_content(content)
            if not sections:
                logger.error("No sections found in file")
                return None
                
            logger.debug(f"Found raw sections: {list(sections.keys())}")
            
            # Clean the content for each section
            cleaned_contents = {}
            for title, text in sections.items():
                logger.debug(f"Processing section: {title}")
                cleaned_text = self.text_processor.clean_text_for_image(text)
                cleaned_contents[title] = cleaned_text
                logger.debug(f"Added cleaned content for section: {title}")
            
            logger.debug(f"Final sections: {list(sections.keys())}")
            logger.debug(f"Final cleaned_contents: {list(cleaned_contents.keys())}")
            
            result = {
                'sections': sections,
                'cleaned_contents': cleaned_contents
            }
            
            # Verify result before returning
            if set(result['sections'].keys()) != set(result['cleaned_contents'].keys()):
                logger.error("Mismatch between sections and cleaned_contents")
                return None
                
            return result
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            return None
