import streamlit as st
import logging
from typing import Dict, Set, Any, Optional
from pathlib import Path
import uuid
import subprocess
from state_manager import AppState
from image_processor import ImageProcessor
from config_manager import Config
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

class BaseUI:
    """Base class for UI components."""
    
    def __init__(self, state: AppState):
        """Initialize UI component.
        
        Args:
            state: Application state manager
        """
        self.state = state
        # Initialize session state if needed
        for key in state.VALID_KEYS:
            if key not in st.session_state:
                st.session_state[key] = getattr(state, key)

class ImageGridUI(BaseUI):
    """Component for rendering the grid of images."""
    
    def __init__(self, state: AppState, image_processor: ImageProcessor):
        """Initialize the image grid UI component.
        
        Args:
            state: Application state manager
            image_processor: Image processor instance
        """
        super().__init__(state)
        self.image_processor = image_processor
    
    def render_image_pair(self, titles, cleaned_contents, image_config):
        """Render a pair of images in two columns.
        
        Args:
            titles: List of two titles to render
            cleaned_contents: Dict of cleaned content for each title
            image_config: Configuration for image generation
        """
        col1, col2 = st.columns(2)
        
        # Process first image
        if titles:
            self._render_single_image(titles[0], cleaned_contents, image_config, col1)
        
        # Process second image if it exists
        if len(titles) > 1:
            self._render_single_image(titles[1], cleaned_contents, image_config, col2)
    
    def _render_single_image(self, title, cleaned_contents, image_config, column):
        """Render a single image with its controls in a column.
        
        Args:
            title: Title of the image
            cleaned_contents: Dict of cleaned content for each title
            image_config: Configuration for image generation
            column: Streamlit column to render in
        """
        with column:
            st.subheader(title)
            cleaned_content = cleaned_contents[title]
            logger.debug(f"Rendering image for {title}")
            
            # Generate or retrieve image
            if title not in self.state.images:
                logger.debug(f"Creating new image for {title}")
                try:
                    image = self.image_processor.create_text_image(
                        text=cleaned_content,
                        config=image_config,
                        show_header_footer=self.state.show_header_footer
                    )
                    logger.debug(f"Successfully created image for {title}")
                    # Update both state and session state
                    current_images = dict(self.state.images)
                    current_images[title] = image
                    self.state.update(images=current_images)
                    logger.debug(f"Updated state with new image for {title}")
                except Exception as e:
                    logger.error(f"Error creating image for {title}: {str(e)}")
                    st.error(f"Failed to create image for {title}")
                    return
            
            # Create checkbox and image container
            check_col, img_col = st.columns([1, 10])
            
            # Get or create unique key for this checkbox
            if title not in self.state.checkbox_keys:
                self.state.update(checkbox_keys={
                    **self.state.checkbox_keys,
                    title: f"checkbox_{str(uuid.uuid4())}"
                })
            checkbox_key = self.state.checkbox_keys[title]
            
            # Checkbox
            with check_col:
                selected = st.checkbox(
                    "Select image",
                    key=checkbox_key,
                    value=self.state.selected_images.get(title, False),
                    label_visibility="collapsed"
                )
                if selected != self.state.selected_images.get(title, False):
                    current_selected = dict(self.state.selected_images)
                    current_selected[title] = selected
                    self.state.update(selected_images=current_selected)
            
            # Image
            with img_col:
                if title in self.state.images:
                    st.image(self.state.images[title], use_column_width=True)
                else:
                    st.error(f"Image for {title} not found in state")
            
            # Debug text expander
            with st.expander("Show cleaned text"):
                st.text_area(
                    "Cleaned text",
                    cleaned_content,
                    height=150,
                    label_visibility="collapsed"
                )

class ConfigurationUI(BaseUI):
    """Handles configuration UI components."""
    
    def __init__(self, state: AppState, config: Config):
        """Initialize configuration UI.
        
        Args:
            state: Application state manager
            config: Configuration manager instance
        """
        super().__init__(state)
        self.config = config
    
    def render(self):
        """Render configuration UI components."""
        st.sidebar.title("Settings")
        with st.sidebar:
            # Select all checkbox
            if st.checkbox("Select All Images", key="select_all_checkbox", value=self.state.select_all):
                if not self.state.select_all:  # Only update if changing to True
                    self.state.update(
                        select_all=True,
                        selected_images={title: True for title in self.state.sections}
                    )
            elif self.state.select_all:  # Only update if changing to False
                self.state.update(
                    select_all=False,
                    selected_images={title: False for title in self.state.sections}
                )

class HeaderSettingsUI(BaseUI):
    """Handles header settings UI components."""
    
    def __init__(self, state: AppState, config: Config):
        """Initialize header settings UI.
        
        Args:
            state: Application state manager
            config: Configuration manager instance
        """
        super().__init__(state)
        self.config = config
    
    def render(self):
        """Render header settings UI components."""
        st.sidebar.subheader("Header Settings")
        header_override = st.sidebar.text_input(
            "Override Header", 
            value="", 
            help="Leave empty to use header from config"
        )
        st.session_state.show_header_footer = st.sidebar.checkbox(
            "Show Header and Footer", 
            value=st.session_state.show_header_footer,
            help="Toggle visibility of header and footer text"
        )
        
        # Font settings
        st.sidebar.subheader("Font Settings")
        
        # Get font configurations from config
        font_paths = self.config['fonts']['paths']
        header_fonts = self.config['fonts']['header_fonts']
        body_fonts = self.config['fonts']['body_fonts']
        
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
        
        # Store header override in session state
        st.session_state.header_override = header_override

class ExportOptionsUI(BaseUI):
    """Handles export options UI components."""
    
    def __init__(self, state: AppState, app: 'App'):
        """Initialize export options UI.
        
        Args:
            state: Application state manager
            app: Main application instance for accessing export methods
        """
        super().__init__(state)
        self.app = app
    
    def render(self):
        """Render export options UI components."""
        st.sidebar.subheader("Export Options")
        
        selected_titles = [title for title, selected in self.state.selected_images.items() if selected]
        
        if selected_titles:
            st.sidebar.write(f"Selected images: {len(selected_titles)}")
            
            # Create two columns for the buttons
            col1, col2 = st.sidebar.columns(2)
            
            # Export to Photos
            with col1:
                if st.button("Save to Photos"):
                    with st.spinner("Saving to Photos..."):
                        results = self.app.photos_ui.save_to_photos(selected_titles)
                        st.session_state.import_results = results
                        st.rerun()
            
            # Export to Drive if available
            if self.app.drive_ui:
                with col2:
                    if st.button("Export to Drive"):
                        with st.spinner("Exporting to Drive..."):
                            self.app.drive_ui.export_to_drive(selected_titles)
                            st.rerun()
        else:
            st.sidebar.write("No images selected")

class FileUploaderUI(BaseUI):
    """UI component for file upload handling."""
    
    def __init__(self, state: AppState, file_processor: 'FileProcessor'):
        """Initialize the file uploader UI component.
        
        Args:
            state: Application state manager
            file_processor: File processor instance for handling uploaded files
        """
        super().__init__(state)
        self.file_processor = file_processor
    
    def handle_file_upload(self, uploaded_file):
        """Process uploaded file and generate collaterals.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
        """
        if uploaded_file:
            logger.info(f"Processing uploaded file: {uploaded_file.name}")
            
            try:
                # Process the file
                logger.debug("Calling file processor...")
                result = self.file_processor.process_file(uploaded_file)
                
                if result and isinstance(result, dict):
                    sections = result.get('sections', {})
                    cleaned_contents = result.get('cleaned_contents', {})
                    
                    logger.debug(f"Received sections keys: {list(sections.keys())}")
                    logger.debug(f"Received cleaned_contents keys: {list(cleaned_contents.keys())}")
                    
                    if not sections or not cleaned_contents:
                        logger.error("Empty sections or cleaned contents")
                        return False
                        
                    if set(sections.keys()) != set(cleaned_contents.keys()):
                        logger.error("Mismatch between sections and cleaned contents")
                        return False
                    
                    # Update state in one atomic operation
                    logger.debug("Updating state...")
                    success = self.state.update(
                        sections=dict(sections),
                        cleaned_contents=dict(cleaned_contents),
                        images={},
                        selected_images={}
                    )
                    
                    if success:
                        st.session_state.processed_file = uploaded_file
                        logger.info(f"Successfully processed file with {len(sections)} sections")
                        return True
                    else:
                        logger.error("State update failed")
                        return False
                else:
                    logger.error("Invalid result from file processor")
                    return False
                    
            except Exception as e:
                logger.error(f"Error processing file: {str(e)}", exc_info=True)
                return False
        return False
    
    def render(self):
        """Render the file uploader widget and handle file uploads."""
        st.sidebar.subheader("Upload File")
        
        uploaded_file = st.sidebar.file_uploader(
            "Choose a file",
            type=['txt', 'md'],
            key='file_uploader',
            label_visibility='collapsed'
        )
        
        if uploaded_file:
            if uploaded_file != st.session_state.get('processed_file'):
                logger.info("New file uploaded, processing...")
                success = self.handle_file_upload(uploaded_file)
                if success:
                    st.rerun()

class MainContentUI(BaseUI):
    """Handles main content area UI components."""
    
    def __init__(self, state: AppState, app: 'App'):
        """Initialize main content UI.
        
        Args:
            state: Application state manager
            app: Main application instance
        """
        super().__init__(state)
        self.app = app
    
    def render(self):
        """Render main content UI components."""
        # Display success message and processing status if present
        if st.session_state.get('success_message') or 'processed_file' in st.session_state:
            with st.expander("Status", expanded=True):
                if st.session_state.get('success_message'):
                    st.success(st.session_state.success_message)
                    if st.button("Clear"):
                        st.session_state.success_message = None
                
                if 'processed_file' in st.session_state:
                    st.info(f"Processing file: {st.session_state.processed_file.name}")
        
        # Create a copy of config to avoid modifying the original
        image_config = self.app.config.copy()
        
        # Add background image path if not already in config
        if 'background_image_path' not in image_config and hasattr(self.app.config, 'background_image_path'):
            image_config['background_image_path'] = self.app.config.background_image_path
        
        # Update config with header override if provided
        if st.session_state.header_override:
            image_config['header'] = st.session_state.header_override
            
        # Add font paths to image config
        image_config['header_font_path'] = st.session_state.header_font_path
        image_config['body_font_path'] = st.session_state.body_font_path
        
        # Update loaded fonts
        self.app.image_processor.load_fonts(
            header_path=st.session_state.header_font_path,
            body_path=st.session_state.body_font_path,
            header_font_size=40,  # Default sizes
            body_font_size=40
        )
        
        # Check if we have sections and cleaned contents
        logger.info("Checking session state for sections and cleaned_contents")
        logger.info(f"Session state keys: {list(st.session_state.keys())}")
        
        if 'sections' in st.session_state and 'cleaned_contents' in st.session_state:
            sections = st.session_state.sections
            cleaned_contents = st.session_state.cleaned_contents
            logger.info(f"Found sections: {list(sections.keys())}")
            logger.info(f"Found cleaned_contents: {list(cleaned_contents.keys())}")
            
            if sections:
                logger.info(f"Found {len(sections)} sections")
                # Process sections in pairs
                sections_items = [(title, content) for title, content in sections.items() if content.strip()]
                logger.info(f"Processing {len(sections_items)} non-empty sections")
                
                for i in range(0, len(sections_items), 2):
                    pair_titles = [sections_items[i][0]]
                    if i + 1 < len(sections_items):
                        pair_titles.append(sections_items[i + 1][0])
                    logger.debug(f"Rendering image pair: {pair_titles}")
                    try:
                        self.app.image_grid.render_image_pair(pair_titles, cleaned_contents, image_config)
                        logger.debug(f"Successfully rendered pair: {pair_titles}")
                    except Exception as e:
                        logger.error(f"Error rendering pair {pair_titles}: {str(e)}")
                        st.error(f"Error rendering images: {str(e)}")
            else:
                st.error("""No valid sections found in the markdown file. Please ensure your file follows this structure:

```markdown
# Collaterals
## Section Title 1
Content for section 1...

## Section Title 2
Content for section 2...
```
""")

class PhotosUI(BaseUI):
    """Handles Photos app integration UI components."""
    
    def __init__(self, state: AppState, app: 'App'):
        """Initialize photos UI.
        
        Args:
            state: Application state manager
            app: Main application instance
        """
        super().__init__(state)
        self.app = app
    
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
            if title not in self.state.images:
                results.append(f"❌ Failed: Image not found for {title}")
                continue
                
            try:
                # Save image to temporary file for Photos import
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    self.state.images[title].save(tmp.name, format='PNG')
                    
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
                            success = self.app.text_collector.add_clipping(
                                source_file=source_file.name,
                                image_file=os.path.basename(tmp.name),
                                text=self.state.cleaned_contents[title],
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

class DriveUI(BaseUI):
    """Handles Google Drive integration UI components."""
    
    def __init__(self, state: AppState, app: 'App'):
        """Initialize drive UI.
        
        Args:
            state: Application state manager
            app: Main application instance
        """
        super().__init__(state)
        self.app = app
    
    def render(self):
        """Render drive UI components."""
        st.sidebar.subheader("Google Drive")
        
        if not self.state.drive_authenticated:
            if st.sidebar.button("Connect Drive"):
                with st.spinner("Connecting to Google Drive..."):
                    if self.app.drive_manager.authenticate():
                        self.state.update(drive_authenticated=True)
                        st.success("Connected to Google Drive!")
                        st.rerun()
                    else:
                        st.error("Failed to connect to Google Drive")
    
    def export_to_drive(self, titles):
        """Export selected images to Google Drive.
        
        Args:
            titles: List of image titles to export
            
        Returns:
            bool: True if all exports were successful
        """
        success = True
        results = []
        
        for title in titles:
            try:
                if title in self.state.exported_files:
                    results.append(f"⚠️ Already exported: {title}")
                    continue
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    # Generate and save image
                    image = self.app.image_processor.create_text_image(
                        text=self.state.cleaned_contents[title],
                        config=self.app.config.to_dict()
                    )
                    image.save(tmp.name)
                    
                    # Upload to Drive
                    result = self.app.drive_manager.upload_file(tmp.name)
                    if result:
                        self.state.update(exported_files=self.state.exported_files | {title})  # Store title instead of path
                        results.append(f"✅ Uploaded to Drive: {title} - {result.get('webViewLink')}")
                        
                        # Save text clipping after successful upload
                        source_file = (st.session_state.get('file_uploader', None) or 
                                     st.session_state.get('processed_file', None))
                        logger.info(f"Found source file: {source_file.name if source_file else 'None'}")
                        if source_file:
                            logger.info(f"Attempting to save clipping for {title} from {source_file.name}")
                            logger.info(f"Text content length: {len(self.state.cleaned_contents[title])}")
                            self.app.text_collector.add_clipping(
                                source_file=source_file.name,
                                image_file=os.path.basename(tmp.name),
                                text=self.state.cleaned_contents[title],
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
