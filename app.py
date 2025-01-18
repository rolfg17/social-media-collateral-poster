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
from ui_components import ImageGridUI, FileUploaderUI, ConfigurationUI, ExportOptionsUI, HeaderSettingsUI, MainContentUI
from file_processor import FileProcessor
from pathlib import Path
import subprocess
import tempfile
import urllib.parse
import io

# Set page config before any other Streamlit commands
st.set_page_config(page_title="Social Media Collateral Generator", layout="wide")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Force reconfiguration of the root logger
)
logger = logging.getLogger(__name__)

# Test log
logger.info("=====================================")
logger.info("Starting application with test log...")
logger.info("=====================================")

logger.info("\n\n Starting application...")
logger.info(f"Command line arguments: {sys.argv}")

class CollateralApp:
    """Main application class for handling social media collateral generation."""
    
    def __init__(self):
        """Initialize the application."""
        self.state = AppState()
        self.config = ConfigManager().load_config()
        self.text_processor = TextProcessor()
        self.file_processor = FileProcessor(self.text_processor)
        self.image_processor = ImageProcessor(self.config.to_dict())
        self.image_grid = ImageGridUI(self.state, self.image_processor)
        self.file_uploader = FileUploaderUI(self.state, self.file_processor)
        self.config_ui = ConfigurationUI(self.state, self.config)
        self.export_ui = ExportOptionsUI(self.state, self)
        self.header_ui = HeaderSettingsUI(self.state, self.config)
        self.main_content = MainContentUI(self.state, self)
        self.initialize_session_state()
        try:
            self.drive_manager = DriveManager()
        except ValueError as e:
            self.drive_manager = None
            logger.warning(f"Google Drive integration not available: {str(e)}")
        
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
        if 'cleaned_contents' not in st.session_state:
            st.session_state.cleaned_contents = {}
        
        # Initialize fonts
        if 'header_font_path' not in st.session_state:
            st.session_state.header_font_path = self.config['fonts']['paths']['Montserrat Light']
        if 'body_font_path' not in st.session_state:
            st.session_state.body_font_path = self.config['fonts']['paths']['FiraSans Regular']
            
        # Load fonts with current paths
        self.image_processor.load_fonts(
            header_path=st.session_state.header_font_path,
            body_path=st.session_state.body_font_path,
            header_font_size=40,  # Default sizes
            body_font_size=40
        )
    
    def update_selection(self, title):
        """Update selection state and handle select all checkbox"""
        st.session_state.selected_images[title] = st.session_state[f"checkbox_{title}"]
        if not st.session_state[f"checkbox_{title}"] and st.session_state.select_all:
            st.session_state.select_all = False

    def save_to_photos(self, titles: list) -> list:
        """Save images to Photos app using AppleScript.
        
        Args:
            titles: List of image titles to save
            
        Returns:
            list: List of results for each save operation
        """
        logger.info(f"Saving {len(titles)} images to Photos")
        results = []
        
        for title in titles:
            if title not in st.session_state.images:
                results.append(f"❌ Failed: Image not found for {title}")
                continue
                
            try:
                # Save image to temporary file for Photos import
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    st.session_state.images[title].save(tmp.name, format='PNG')
                    
                    # Create AppleScript command
                    script = f'''
                    tell application "Photos"
                        activate
                        delay 1
                        import POSIX file "{tmp.name}"
                    end tell
                    '''
                    
                    # Run AppleScript
                    result = subprocess.run(['osascript', '-e', script], 
                                         capture_output=True, 
                                         text=True)
                    
                    if result.returncode == 0:
                        # Get source filename from either file_uploader or processed_file
                        source_file = (st.session_state.get('file_uploader', None) or 
                                     st.session_state.get('processed_file', None))
                        if source_file:
                            logger.info(f"Adding text clipping for {title}")
                            success = self.text_collector.add_clipping(
                                source_file=source_file.name,
                                image_file=os.path.basename(tmp.name),
                                text=st.session_state.cleaned_contents[title],
                                headline=title,
                                timestamp=None  # Will use current time
                            )
                            if success:
                                results.append(f"✅ Success: Saved image and text for {title}")
                            else:
                                results.append(f"⚠️ Warning: Saved image but failed to save text for {title}")
                    else:
                        logger.error(f"Error importing {title}: {result.stderr}")
                        results.append(f"❌ Failed: {result.stderr} - {title}")
                    
                    # Clean up temporary file
                    os.unlink(tmp.name)
                    
            except Exception as e:
                logger.error(f"Exception in save_to_photos: {str(e)}")
                results.append(f"❌ Failed: {str(e)} - {title}")
        
        # Store results in session state
        st.session_state.import_results = results
        
        return results

    def export_to_drive(self, titles):
        """Export selected images to Google Drive.
        
        Args:
            titles: List of image titles to export
            
        Returns:
            bool: True if all exports were successful
        """
        if not self.drive_manager or not st.session_state.drive_authenticated:
            return False
            
        results = []
        success = True
        
        # Initialize exported_files if not present
        if 'exported_files' not in st.session_state:
            st.session_state.exported_files = set()
        
        for title in titles:
            if title not in st.session_state.images:
                results.append(f"❌ Failed: Image not found for {title}")
                success = False
                continue
                
            try:
                # Save image to temporary file for Drive upload
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    st.session_state.images[title].save(tmp.name, format='PNG')
                    
                    result = self.drive_manager.upload_file(tmp.name)
                    if result:
                        st.session_state.exported_files.add(title)  # Store title instead of path
                        results.append(f"✅ Uploaded to Drive: {title} - {result.get('webViewLink')}")
                        
                        # Save text clipping after successful upload
                        source_file = (st.session_state.get('file_uploader', None) or 
                                     st.session_state.get('processed_file', None))
                        logger.info(f"Found source file: {source_file.name if source_file else 'None'}")
                        if source_file:
                            logger.info(f"Attempting to save clipping for {title} from {source_file.name}")
                            logger.info(f"Text content length: {len(st.session_state.cleaned_contents[title])}")
                            self.text_collector.add_clipping(
                                source_file=source_file.name,
                                image_file=os.path.basename(tmp.name),
                                text=st.session_state.cleaned_contents[title],
                                headline=title,
                                timestamp=None  # Will use current time
                            )
                            logger.info("Finished add_clipping call")
                    else:
                        results.append(f"❌ Failed to upload: {title}")
                        success = False
                    
                    # Clean up temporary file
                    os.unlink(tmp.name)
                    
            except Exception as e:
                logger.error(f"Error in export_to_drive: {str(e)}")
                results.append(f"❌ Failed: {str(e)} - {title}")
                success = False
        
        # Store results in session state
        st.session_state.import_results = results
        
        return success

    def handle_file_upload(self, uploaded_file):
        """Process uploaded file and generate collaterals."""
        logger.info(f"Processing uploaded file: {uploaded_file.name}")
        
        try:
            content = uploaded_file.read().decode('utf-8')
            logger.debug(f"File content length: {len(content)}")
            logger.debug(f"Content preview: {content[:200]}...")  # Show first 200 chars
            
            # Reset file pointer after reading
            uploaded_file.seek(0)
            
            if "# Prompt" in content:
                logger.info("Processing newsletter content")
                sections = self._process_newsletter(content, uploaded_file)
            elif "# Collaterals" in content:
                logger.info("Processing collaterals content")
                sections = self.text_processor.parse_markdown_content(content, self.config)
            else:
                logger.error("Invalid file format: missing required sections")
                st.error("File must contain either '# Prompt' or '# Collaterals' section")
                return None
                
            if sections:
                logger.debug(f"Found {len(sections)} sections")
                logger.debug(f"Section titles: {list(sections.keys())}")
                
                # Clean text for each section
                cleaned_contents = {}
                for title, text in sections.items():
                    logger.debug(f"Cleaning text for section: {title}")
                    cleaned_contents[title] = self.text_processor.clean_text_for_image(text)
                    logger.debug(f"Cleaned content length for {title}: {len(cleaned_contents[title])}")
                
                # Store cleaned contents in state
                logger.debug("Storing cleaned contents in state")
                self.state.update(cleaned_contents=cleaned_contents)
                
                return sections, cleaned_contents
            
            logger.error("No sections found in file")
            return None
                
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            st.error(f"Error processing file: {str(e)}")
            return None

    def update_selection(self, title):
        """Update selection state and handle select all checkbox"""
        st.session_state.selected_images[title] = st.session_state[f"checkbox_{title}"]
        if not st.session_state[f"checkbox_{title}"] and st.session_state.select_all:
            st.session_state.select_all = False

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
    
    # Render main content
    app.main_content.render()

if __name__ == "__main__":
    import sys
    import argparse
    from pathlib import Path
    import logging
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True  # Force reconfiguration of the root logger
    )
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
                    content = app.handle_file_upload(mock_file)
                    if content:
                        logger.info("File processed, starting main UI")
                    else:
                        logger.error("Failed to process file")
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
