"""Module for collecting and storing text clippings from processed images."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TextCollector:
    """Handles collection and storage of text clippings from processed images."""
    
    def __init__(self, vault_path: str):
        """Initialize the TextCollector.
        
        Args:
            vault_path: Path to the Obsidian vault
        """
        self.vault_path = Path(vault_path)
        self.clippings_file = self.vault_path / "text_clippings.json"
        
    def add_clipping(self, 
                     source_file: str, 
                     image_file: str, 
                     text: str,
                     headline: Optional[str] = None,
                     timestamp: Optional[str] = None) -> bool:
        """Add a new text clipping to the collection.
        
        Args:
            source_file: Name of the source markdown file
            image_file: Name of the generated image file
            text: The text content from the image
            headline: Optional headline text
            timestamp: Optional timestamp string
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Adding clipping for {source_file}")
            
            # Create new clipping entry
            clipping = {
                "source_file": Path(source_file).name,
                "image_file": Path(image_file).name,
                "headline": headline,
                "text": text,
                "timestamp": timestamp or datetime.now().isoformat()
            }
            
            # Load existing clippings or create new structure
            if self.clippings_file.exists():
                with open(self.clippings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"clippings": []}
            
            # Add new clipping
            data["clippings"].append(clipping)
            
            # Save updated clippings
            with open(self.clippings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add text clipping: {str(e)}")
            return False
