import streamlit as st
from pathlib import Path
import subprocess
import os
import tempfile
import logging
import sys
from image_processor import ImageProcessor, FONT_CONFIG
from config_manager import load_config
from text_processor import parse_markdown_content, clean_text_for_image
from drive_manager import DriveManager
from text_collector import TextCollector
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
        self.config = load_config()
        self.image_processor = ImageProcessor(self.config.to_dict())
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
        if 'selected_images' not in st.session_state:
            st.session_state.selected_images = {}
        if 'select_all' not in st.session_state:
            st.session_state.select_all = False
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

    def save_to_photos(self, image_paths: list) -> list:
        """Save images to Photos app using AppleScript."""
        logger.info(f"Saving {len(image_paths)} images to Photos")
        
        results = []
        for path in image_paths:
            # Create AppleScript command
            script = f'''
            tell application "Photos"
                activate
                delay 1
                import POSIX file "{path}"
            end tell
            '''
            
            try:
                # Run AppleScript
                result = subprocess.run(['osascript', '-e', script], 
                                     capture_output=True, 
                                     text=True)
                
                if result.returncode == 0:
                    # Save text clipping after successful save to Photos
                    for title, temp_path in st.session_state.get('temp_image_paths', []):
                        if temp_path == path:
                            # Get source filename from either file_uploader or processed_file
                            source_file = (st.session_state.get('file_uploader', None) or 
                                         st.session_state.get('processed_file', None))
                            if source_file:
                                logger.info(f"Adding text clipping for {title}")
                                success = self.text_collector.add_clipping(
                                    source_file=source_file.name,
                                    image_file=os.path.basename(path),
                                    text=st.session_state.cleaned_contents[title],
                                    headline=title,
                                    timestamp=None  # Will use current time
                                )
                                if success:
                                    results.append(f"✅ Success: Saved image and text for {title}")
                                else:
                                    results.append(f"⚠️ Warning: Saved image but failed to save text for {title}")
                            break
                else:
                    logger.error(f"Error importing {path}: {result.stderr}")
                    results.append(f"❌ Failed: {result.stderr} - {path}")
                    
            except Exception as e:
                logger.error(f"Exception in save_to_photos: {str(e)}")
                results.append(f"❌ Failed: {str(e)} - {path}")
        
        # Store results in session state
        st.session_state.import_results = results
        
        return results

    def export_to_drive(self, image_paths):
        """Export selected images to Google Drive.
        
        Args:
            image_paths: List of paths to images to export
            
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
        
        for path in image_paths:
            # Skip if already exported
            if path in st.session_state.exported_files:
                results.append(f"⏭️ Already exported: {os.path.basename(path)}")
                continue
                
            try:
                result = self.drive_manager.upload_file(path)
                if result:
                    st.session_state.exported_files.add(path)
                    results.append(f"✅ Uploaded to Drive: {os.path.basename(path)} - {result.get('webViewLink')}")
                    
                    # Save text clipping after successful upload to Drive
                    for title, temp_path in st.session_state.get('temp_image_paths', []):
                        if temp_path == path:
                            # Get source filename from either file_uploader or processed_file
                            source_file = (st.session_state.get('file_uploader', None) or 
                                         st.session_state.get('processed_file', None))
                            logger.info(f"Found source file: {source_file.name if source_file else 'None'}")
                            if source_file:
                                logger.info(f"Attempting to save clipping for {title} from {source_file.name}")
                                logger.info(f"Text content length: {len(st.session_state.cleaned_contents[title])}")
                                self.text_collector.add_clipping(
                                    source_file=source_file.name,
                                    image_file=os.path.basename(path),
                                    text=st.session_state.cleaned_contents[title],
                                    headline=title,
                                    timestamp=None  # Will use current time
                                )
                                logger.info("Finished add_clipping call")
                            break
                else:
                    results.append(f"❌ Failed to upload: {path}")
                    success = False
            except Exception as e:
                results.append(f"❌ Upload failed: {str(e)} - {path}")
                success = False
        
        # Show results in Streamlit
        if results:
            st.session_state.import_results = results
        
        return success

    def handle_file_upload(self, uploaded_file):
        """Process uploaded file and generate collaterals."""
        try:
            content = uploaded_file.read().decode()
            
            # Reset file pointer after reading
            uploaded_file.seek(0)
            
            # Store uploaded file in session state
            st.session_state.file_uploader = uploaded_file
            
            if "# Prompt" in content:
                logger.info("Processing newsletter content")
                return self._process_newsletter(content, uploaded_file)
            elif "# Collaterals" in content:
                return content
            else:
                st.error("File must contain either '# Prompt' or '# Collaterals' section")
                return None
                
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return None

def main():
    """Main application entry point."""
    
    app = CollateralApp()
    
    # Title in main area
    st.title("Social Media Collateral Images")
    
    # Sidebar
    st.sidebar.title("Settings")
    with st.sidebar:
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a markdown file", 
            type=['md'], 
            help="Upload either a newsletter file with a # Prompt section or a pre-generated collaterals file"
        )
        
        # Select all checkbox
        if st.checkbox("Select All Images", key="select_all_checkbox", value=st.session_state.select_all):
            st.session_state.select_all = True
            for title in st.session_state.selected_images:
                st.session_state.selected_images[title] = True
        else:
            if st.session_state.select_all:
                st.session_state.select_all = False
        
        # Export options
        st.write("### Export Options")
        
        col1, col2 = st.columns(2)
        with col1:
            # Save to Photos button
            if st.button("Save to Photos", key="save_to_photos"):
                logger.info("Save to Photos button clicked")
                # Get selected image paths
                selected_paths = [
                    path for title, path in st.session_state.get('temp_image_paths', []) 
                    if st.session_state.selected_images.get(title, False)
                ]
                logger.info(f"Selected paths: {selected_paths}")
                
                if selected_paths:
                    logger.info(f"Saving {len(selected_paths)} images to Photos")
                    # Save temp_image_paths to session state for text collector
                    st.session_state.temp_image_paths = st.session_state.get('temp_image_paths', [])
                    results = app.save_to_photos(selected_paths)
                    logger.info(f"Save to photos results: {results}")
                    
                    # Show results
                    for result in results:
                        if isinstance(result, subprocess.CompletedProcess):
                            if result.returncode == 0:
                                st.success(f"Successfully imported {result.args[-1]}")
                            else:
                                st.error(f"Error importing {result.args[-1]}: {result.stderr}")
                else:
                    st.warning("Please select at least one image to save")
        
        with col2:
            # Export to Drive button
            drive_button_disabled = app.drive_manager is None
            if drive_button_disabled:
                st.button("Export to Drive", disabled=True, help="Google Drive integration not configured")
            else:
                if not st.session_state.drive_authenticated and st.button("Connect Drive"):
                    with st.spinner("Connecting to Google Drive..."):
                        if app.drive_manager.authenticate():
                            st.session_state.drive_authenticated = True
                            st.success("Connected to Google Drive!")
                            st.rerun()
                        else:
                            st.error("Failed to connect to Google Drive")
                
                elif st.session_state.drive_authenticated and st.button("Export to Drive"):
                    selected_paths = [path for title, path in st.session_state.get('temp_image_paths', []) 
                                   if st.session_state.selected_images.get(title, False)]
                    if not selected_paths:
                        st.warning("Please select at least one image to export")
                    else:
                        with st.spinner("Exporting to Google Drive..."):
                            app.export_to_drive(selected_paths)
        
        # Header override setting
        st.sidebar.subheader("Header Settings")
        header_override = st.sidebar.text_input("Override Header", value="", help="Leave empty to use header from config")
        st.session_state.show_header_footer = st.sidebar.checkbox("Show Header and Footer", 
                                                                value=st.session_state.show_header_footer,
                                                                help="Toggle visibility of header and footer text")
        
        # Font settings in sidebar
        st.sidebar.subheader("Font Settings")
        
        # Get font configurations from config
        font_paths = app.config['fonts']['paths']
        header_fonts = app.config['fonts']['header_fonts']
        body_fonts = app.config['fonts']['body_fonts']
        
        header_font = st.sidebar.selectbox(
            "Header/Footer Font",
            header_fonts,
            index=0
        )
        
        body_font = st.sidebar.selectbox(
            "Body Font",
            body_fonts,
            index=0
        )
        
        # Store font paths in session state
        st.session_state.header_font_path = font_paths[header_font]
        st.session_state.body_font_path = font_paths[body_font]
        
        # Update loaded fonts when paths change
        app.image_processor.load_fonts(
            header_path=st.session_state.header_font_path,
            body_path=st.session_state.body_font_path,
            header_font_size=40,  # Default sizes
            body_font_size=40
        )
    
    # Create a copy of config to avoid modifying the original
    image_config = app.config.copy()
    
    # Ensure background_image_path is included
    if 'background_image_path' not in image_config and hasattr(app.config, 'background_image_path'):
        image_config['background_image_path'] = app.config.background_image_path
    
    # Update config with header override if provided
    if header_override:
        image_config['header'] = header_override
        
    # Add font paths to image config
    image_config['header_font_path'] = st.session_state.header_font_path
    image_config['body_font_path'] = st.session_state.body_font_path
    
    # Handle file upload and image generation
    current_file = uploaded_file if uploaded_file is not None else st.session_state.get('file_uploader')
    
    # Check if we need to reprocess content by comparing content hash
    should_reprocess = False
    if current_file:
        current_content = current_file.read()
        current_file.seek(0)  # Reset file pointer after reading
        content_hash = hash(current_content)
        
        should_reprocess = (
            'processed_sections' not in st.session_state or  # First time processing
            'last_content_hash' not in st.session_state or  # No hash stored
            st.session_state.last_content_hash != content_hash  # Content changed
        )
    
    if current_file:
        st.info(f"Processing file: {current_file.name}")
        
        if should_reprocess:
            # Process new content
            content = app.handle_file_upload(current_file)
            if content:
                # Parse and clean content
                sections = parse_markdown_content(content, image_config)
                if sections:
                    # Cache the processed content and content hash
                    st.session_state.processed_sections = sections
                    st.session_state.cleaned_contents = {
                        title: clean_text_for_image(content) 
                        for title, content in sections.items() 
                        if content.strip()
                    }
                    st.session_state.last_content_hash = content_hash
                else:
                    st.error("""No valid sections found in the markdown file. Please ensure your file follows this structure:

```markdown
# Collaterals
## Section Title 1
Content for section 1...

## Section Title 2
Content for section 2...
```

Note: 
- Must start with '# Collaterals' header
- Each section must start with '## ' (level 2 header)
- Content must be placed under each section header
""")
                    return
        
        # Use cached content if available
        if 'processed_sections' in st.session_state:
            sections = st.session_state.processed_sections
            cleaned_contents = st.session_state.cleaned_contents
            
            # Status area for import results
            if 'import_results' in st.session_state and st.session_state.import_results:
                with st.expander("Export Results", expanded=True):
                    success_count = sum(1 for result in st.session_state.import_results if result.startswith('✅'))
                    failure_count = len([r for r in st.session_state.import_results if r.startswith('❌')])
                    st.write(f"✅ {success_count} successful exports, ❌ {failure_count} failed exports")
                    
                    # Display each result, with clickable links for Drive exports
                    for result in st.session_state.import_results:
                        if " - http" in result:  # It's a Drive result with a link
                            text, link = result.rsplit(" - ", 1)
                            st.markdown(f"{text} - [View in Drive]({link})")
                        else:
                            st.write(result)
                    
                    # Add status message about text clippings
                    clippings_path = Path(app.config['obsidian_vault_path']) / "text_clippings.json"
                    if clippings_path.exists():
                        st.write("✅ Text clippings saved successfully")
                    else:
                        st.markdown("❌ Text clippings file not found")
                    
                    if st.button("Clear Results"):
                        st.session_state.import_results = []
                        st.rerun()
            
            # Process images in pairs
            sections_items = [(title, content) for title, content in sections.items() if content.strip()]
            temp_image_paths = []
            
            for i in range(0, len(sections_items), 2):
                # Create a row for each pair of images
                col1, col2 = st.columns(2)
                
                # Process first image in the pair
                title, _ = sections_items[i]
                with col1:
                    st.subheader(title)
                    # Use cached cleaned content and image if available
                    cleaned_content = cleaned_contents[title]
                    if title not in st.session_state.images:
                        image = app.image_processor.create_text_image(
                            text=cleaned_content,
                            config=image_config,
                            show_header_footer=st.session_state.show_header_footer
                        )
                        st.session_state.images[title] = image
                    # Initialize this image's state if not present
                    if title not in st.session_state.selected_images:
                        st.session_state.selected_images[title] = st.session_state.select_all
                    
                    # Create checkbox and image container
                    check_col, img_col = st.columns([1, 10])
                    
                    # Checkbox
                    with check_col:
                        st.checkbox(
                            "Select image",
                            key=f"checkbox_{title}",
                            value=st.session_state.selected_images.get(title, False),
                            on_change=app.update_selection,
                            args=(title,),
                            label_visibility="collapsed"
                        )
                    
                    # Image
                    with img_col:
                        st.image(st.session_state.images[title], use_column_width=True)
                    
                    # Show the cleaned text for debugging
                    with st.expander("Show cleaned text"):
                        st.text_area("Cleaned text", cleaned_content, height=150, label_visibility="collapsed")
                
                # Process second image in the pair (if it exists)
                if i + 1 < len(sections_items):
                    title, _ = sections_items[i + 1]
                    with col2:
                        st.subheader(title)
                        # Use cached cleaned content and image if available
                        cleaned_content = cleaned_contents[title]
                        if title not in st.session_state.images:
                            image = app.image_processor.create_text_image(
                                text=cleaned_content,
                                config=image_config,
                                show_header_footer=st.session_state.show_header_footer
                            )
                            st.session_state.images[title] = image
                        
                        # Initialize this image's state if not present
                        if title not in st.session_state.selected_images:
                            st.session_state.selected_images[title] = st.session_state.select_all
                        
                        # Create checkbox and image container
                        check_col, img_col = st.columns([1, 10])
                        
                        # Checkbox
                        with check_col:
                            st.checkbox(
                                "Select image",
                                key=f"checkbox_{title}",
                                value=st.session_state.selected_images.get(title, False),
                                on_change=app.update_selection,
                                args=(title,),
                                label_visibility="collapsed"
                            )
                        
                        # Image
                        with img_col:
                            st.image(st.session_state.images[title], use_column_width=True)
                        
                        # Show the cleaned text for debugging
                        with st.expander("Show cleaned text"):
                            st.text_area("Cleaned text", cleaned_content, height=150, label_visibility="collapsed")
            
            # Cleanup function to remove temporary files
            def cleanup():
                for _, path in temp_image_paths:
                    try:
                        os.unlink(path)
                    except:
                        pass
            
            # Register cleanup function
            import atexit
            atexit.register(cleanup)

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
