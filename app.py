import streamlit as st
import logging
import sys
import os
from text_processor import TextProcessor
from image_processor import ImageProcessor
from config_manager import ConfigManager
from drive_manager import DriveManager
from text_collector import TextCollector
from state_manager import AppState
from ui_components import ImageGridUI, FileUploaderUI, ConfigurationUI, ExportOptionsUI, HeaderSettingsUI, MainContentUI, DriveUI, PhotosUI
from file_processor import FileProcessor
from pathlib import Path
import subprocess
import tempfile
import urllib.parse
import io

# Set page config before any other Streamlit commands
st.set_page_config(page_title="Social Media Collateral Generator", layout="wide")

# Set up logging
def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific logger levels
    logging.getLogger('image_processor').setLevel(logging.INFO)
    logging.getLogger('PIL').setLevel(logging.WARNING)  # Reduce Pillow logging
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("=====================================")
    logger.info("Starting application with test log...")
    logger.info("=====================================")
    logger.info("\n Starting application...")
    logger.info(f"Command line arguments: {sys.argv}")

setup_logging()

logger = logging.getLogger(__name__)

# Test log
logger.info("\n\n Starting application...")
logger.info(f"Command line arguments: {sys.argv}")

class CollateralApp:
    """Main application class for handling social media collateral generation."""
    
    def __init__(self):
        """Initialize the application."""
        self.state = AppState()
        self.config = ConfigManager().load_config()
        
        # Initialize processors
        self.text_processor = TextProcessor()
        self.file_processor = FileProcessor(self.text_processor)
        self.image_processor = ImageProcessor(self.config.to_dict())
        
        # Initialize UI components that don't need app reference
        self.config_ui = ConfigurationUI(self.state, self.config)
        self.header_ui = HeaderSettingsUI(self.state, self.config)
        self.file_uploader = FileUploaderUI(self.state, self.file_processor, self)
        
        # Initialize UI components that need app reference
        self.image_grid = ImageGridUI(self.state, self)
        self.main_content = MainContentUI(self.state, self)
        self.photos_ui = PhotosUI(self.state, self)
        self.export_ui = ExportOptionsUI(self.state, self)
        
        self.initialize_session_state()
        try:
            self.drive_manager = DriveManager()
            self.drive_ui = DriveUI(self.state, self)
        except Exception as e:
            logger.error(f"Failed to initialize Drive: {e}")
            self.drive_manager = None
            self.drive_ui = None
        
        # Initialize text collector 
        self.text_collector = TextCollector(self.config['obsidian_vault_path'])

    def initialize_session_state(self):
        """Initialize all session state variables."""
        self.state.sync_with_session()
        if 'selected_images' not in st.session_state:
            st.session_state.selected_images = {}
        if 'import_results' not in st.session_state:
            st.session_state.import_results = []
        if 'show_header_footer' not in st.session_state:
            st.session_state.show_header_footer = True
        if 'drive_authenticated' not in st.session_state:
            st.session_state.drive_authenticated = False
        if 'exported_files' not in st.session_state:
            st.session_state.exported_files = set()
        if 'images' not in st.session_state:
            st.session_state.images = {}
        if 'grid_images' not in st.session_state:
            st.session_state.grid_images = {}
        if 'cleaned_contents' not in st.session_state:
            st.session_state.cleaned_contents = {}
    
        # Initialize font paths in session state
        if 'header_font_path' not in st.session_state:
            if self.config.fonts.header_fonts and self.config.fonts.header_fonts[0] in self.config.fonts.paths:
                st.session_state.header_font_path = self.config.fonts.paths[self.config.fonts.header_fonts[0]]
            else:
                st.session_state.header_font_path = "/System/Library/Fonts/Helvetica.ttc"
                
        if 'body_font_path' not in st.session_state:
            if self.config.fonts.body_fonts and self.config.fonts.body_fonts[0] in self.config.fonts.paths:
                st.session_state.body_font_path = self.config.fonts.paths[self.config.fonts.body_fonts[0]]
            else:
                st.session_state.body_font_path = "/System/Library/Fonts/Helvetica.ttc"

    def handle_file_upload(self, file):
        """Process uploaded file and generate collaterals.
        
        Args:
            file: The uploaded file object
            
        Returns:
            Tuple of (sections, cleaned_contents) if successful, None otherwise
        """
        return self.file_processor.process_file(file)

def main():
    """Main application entry point."""
    
    st.title("Social Media Collateral Poster")
    
    # Initialize app
    app = CollateralApp()
    
    # Sidebar title
    st.sidebar.title("Settings")
    
    # Render sidebar components
    with st.sidebar:
        # File uploader first
        app.file_uploader.render()
        # Then other sidebar components
        app.config_ui.render()
        app.export_ui.render()
        app.header_ui.render()
        if app.drive_ui:
            app.drive_ui.render()
    
    # Render main content
    app.main_content.render()
    app.image_grid.render()

if __name__ == "__main__":
    import sys
    import argparse
    from pathlib import Path
    import logging
    
    # Set up logging
    logger = logging.getLogger(__name__)

    # Test log
    logger.info("=====================================")
    logger.info("Starting application with test log...")
    logger.info("=====================================")

    logger.info("\n\n Starting application...")
    logger.info(f"Command line arguments: {sys.argv}")
    
    parser = argparse.ArgumentParser(description='Social Media Collateral Generator')
    parser.add_argument('--file', type=str, help='Path to markdown file to process')
    args = parser.parse_args()
    
    logger.info(f"Parsed arguments: {args}")
    
    # Debug logging
    if args.file:
        # Clean up any potential escaping in the path
        clean_path = args.file.replace('\\', '')
        file_path = Path(clean_path)
        logger.info(f"Processing file: {file_path}")
        logger.info(f"File exists: {file_path.exists()}")
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"Successfully read file, first 100 chars: {content[:100]}")
                    # Create a mock uploaded file and store in session state
                    from types import SimpleNamespace
                    mock_file = SimpleNamespace(
                        name=file_path.name,
                        read=lambda: content.encode('utf-8'),
                        seek=lambda x: None  # Add mock seek method
                    )
                    st.session_state.processed_file = mock_file  # Store as processed_file instead of file_uploader
                    logger.info("File loaded into session state")
                    # Initialize app and process file without running the main loop
                    app = CollateralApp()
                    # Don't call main() here, let the script's main entry point handle it
            except Exception as e:
                logger.error(f"Error reading file: {e}")
        else:
            logger.error(f"File does not exist: {file_path}")
    else:
        logger.info("No file argument provided")
    
    # Initialize the app
    logger.info("Initializing main app...")
    main()
    logger.info("Main app initialized")
