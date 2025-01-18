import streamlit as st
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ImageGridUI:
    """Component for rendering the grid of images."""
    
    def __init__(self, state, image_processor):
        """Initialize the image grid UI component.
        
        Args:
            state: AppState instance
            image_processor: ImageProcessor instance
        """
        self.state = state
        self.image_processor = image_processor
        
        # Initialize checkbox keys in session state if not present
        if 'checkbox_keys' not in st.session_state:
            st.session_state.checkbox_keys = {}
    
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
            
            # Initialize selection state if needed
            if title not in self.state.selected_images:
                logger.debug(f"Initializing selection state for {title}")
                current_selected = dict(self.state.selected_images)
                current_selected[title] = self.state.select_all
                self.state.update(selected_images=current_selected)
            
            # Create checkbox and image container
            check_col, img_col = st.columns([1, 10])
            
            # Get or create unique key for this checkbox from session state
            if title not in st.session_state.checkbox_keys:
                st.session_state.checkbox_keys[title] = f"checkbox_{str(uuid.uuid4())}"
            checkbox_key = st.session_state.checkbox_keys[title]
            
            # Checkbox
            with check_col:
                selected = st.checkbox(
                    "Select image",
                    key=checkbox_key,
                    value=self.state.selected_images.get(title, False),
                    label_visibility="collapsed"
                )
                if selected != self.state.selected_images.get(title):
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

class ConfigurationUI:
    """Handles configuration UI components."""
    
    def __init__(self, state, config):
        """Initialize configuration UI.
        
        Args:
            state: Application state manager
            config: Configuration manager instance
        """
        self.state = state
        self.config = config
        if 'select_all' not in st.session_state:
            st.session_state.select_all = False
    
    def render(self):
        """Render configuration UI components."""
        st.sidebar.title("Settings")
        with st.sidebar:
            # Select all checkbox
            if st.checkbox("Select All Images", key="select_all_checkbox", value=st.session_state.select_all):
                st.session_state.select_all = True
                for key in st.session_state.selected_images:
                    st.session_state.selected_images[key] = True
            else:
                st.session_state.select_all = False

class HeaderSettingsUI:
    """Handles header settings UI components."""
    
    def __init__(self, state, config):
        """Initialize header settings UI.
        
        Args:
            state: Application state manager
            config: Configuration manager instance
        """
        self.state = state
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

class ExportOptionsUI:
    """Handles export options UI components."""
    
    def __init__(self, state, app):
        """Initialize export options UI.
        
        Args:
            state: Application state manager
            app: Main application instance for accessing export methods
        """
        self.state = state
        self.app = app
    
    def render(self):
        """Render export options UI components."""
        st.sidebar.write("### Export Options")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            # Save to Photos button
            if st.button("Save to Photos", key="save_to_photos"):
                logger.info("Save to Photos button clicked")
                # Get selected image titles
                selected_titles = [title for title, selected in st.session_state.selected_images.items() if selected]
                logger.info(f"Selected titles: {selected_titles}")
                
                if selected_titles:
                    logger.info(f"Saving {len(selected_titles)} images to Photos")
                    results = self.app.save_to_photos(selected_titles)
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
            drive_button_disabled = self.app.drive_manager is None
            if drive_button_disabled:
                st.button("Export to Drive", disabled=True, help="Google Drive integration not configured")
            else:
                if not st.session_state.drive_authenticated and st.button("Connect Drive"):
                    with st.spinner("Connecting to Google Drive..."):
                        if self.app.drive_manager.authenticate():
                            st.session_state.drive_authenticated = True
                            st.success("Connected to Google Drive!")
                            st.rerun()
                        else:
                            st.error("Failed to connect to Google Drive")
                
                elif st.session_state.drive_authenticated and st.button("Export to Drive"):
                    selected_titles = [title for title, selected in st.session_state.selected_images.items() if selected]
                    if not selected_titles:
                        st.warning("Please select at least one image to export")
                    else:
                        with st.spinner("Exporting to Google Drive..."):
                            self.app.export_to_drive(selected_titles)

class FileUploaderUI:
    """UI component for file upload handling."""
    
    def __init__(self, state, file_processor):
        """Initialize the file uploader UI component.
        
        Args:
            state: AppState instance
            file_processor: FileProcessor instance for handling uploaded files
        """
        self.state = state
        self.file_processor = file_processor
        
    def render(self):
        """Render the file uploader widget and handle file uploads."""
        uploaded_file = st.file_uploader(
            "Choose a markdown file", 
            type=['md'], 
            help="Upload either a newsletter file with a # Prompt section or a pre-generated collaterals file",
            key="file_uploader"
        )
        
        if uploaded_file:
            # Store the uploaded file in session state
            if 'processed_file' not in st.session_state or st.session_state.processed_file != uploaded_file:
                st.session_state.processed_file = uploaded_file
                logger.info(f"New file uploaded: {uploaded_file.name}")
                try:
                    content_preview = uploaded_file.read().decode('utf-8')[:200]
                    uploaded_file.seek(0)  # Reset file pointer
                    logger.info(f"Content preview: {content_preview}")
                    
                    # Process the file
                    logger.info("Processing uploaded file...")
                    content = self.file_processor.process_file(uploaded_file)
                    
                    if content:
                        sections, cleaned_contents = content
                        if sections:
                            logger.info(f"Successfully processed {len(sections)} sections")
                            # Store processed content
                            st.session_state.processed_sections = sections
                            st.session_state.cleaned_contents = cleaned_contents
                            st.session_state.success_message = f"Successfully processed {len(sections)} sections"
                        else:
                            logger.error("No sections found in file")
                            st.error("No sections found in file")
                    else:
                        logger.error("Failed to process file")
                        st.error("Failed to process file")
                except Exception as e:
                    logger.error(f"Error processing file: {str(e)}", exc_info=True)
                    st.error(f"Error processing file: {str(e)}")

class MainContentUI:
    """Handles main content area UI components."""
    
    def __init__(self, state, app):
        """Initialize main content UI.
        
        Args:
            state: Application state manager
            app: Main application instance
        """
        self.state = state
        self.app = app
    
    def render(self):
        """Render main content UI components."""
        # Display success message if present
        if st.session_state.get('success_message'):
            with st.expander("Success", expanded=True):
                st.success(st.session_state.success_message)
                if st.button("Clear"):
                    st.session_state.success_message = None
        
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
        
        # Check if we need to reprocess content by comparing content hash
        should_reprocess = False
        if 'processed_file' in st.session_state:
            logger.info(f"Current file detected: {st.session_state.processed_file.name}")
            current_content = st.session_state.processed_file.read()
            st.session_state.processed_file.seek(0)  # Reset file pointer after reading
            content_hash = hash(current_content)
            logger.debug(f"Content hash: {content_hash}")
            
            should_reprocess = (
                'processed_sections' not in st.session_state or  # First time processing
                'last_content_hash' not in st.session_state or  # No hash stored
                st.session_state.last_content_hash != content_hash  # Content changed
            )
            logger.info(f"Should reprocess: {should_reprocess}")
        
        if 'processed_file' in st.session_state:
            st.info(f"Processing file: {st.session_state.processed_file.name}")
            
            if should_reprocess:
                logger.info("Processing new content")
                # Process new content
                content = self.app.handle_file_upload(st.session_state.processed_file)
                if content:
                    logger.info("Content processed successfully")
                    # Parse and clean content
                    sections, cleaned_contents = content
                    if sections:
                        logger.info(f"Found {len(sections)} sections")
                        # Cache the processed content and content hash
                        st.session_state.processed_sections = sections
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
                        clippings_path = Path(self.app.config['obsidian_vault_path']) / "text_clippings.json"
                        if clippings_path.exists():
                            st.write("✅ Text clippings saved successfully")
                        else:
                            st.markdown("❌ Text clippings file not found")
                        
                        if st.button("Clear Results"):
                            st.session_state.import_results = []
                            st.rerun()
                
                # Main content area - render images
                if 'processed_sections' in st.session_state and 'cleaned_contents' in st.session_state:
                    sections_items = [(title, content) for title, content in st.session_state.processed_sections.items() if content.strip()]
                    logger.info(f"Processing {len(sections_items)} sections")
                    
                    for i in range(0, len(sections_items), 2):
                        pair_titles = [sections_items[i][0]]
                        if i + 1 < len(sections_items):
                            pair_titles.append(sections_items[i + 1][0])
                        logger.debug(f"Rendering image pair: {pair_titles}")
                        try:
                            self.app.image_grid.render_image_pair(pair_titles, st.session_state.cleaned_contents, image_config)
                            logger.debug(f"Successfully rendered pair: {pair_titles}")
                        except Exception as e:
                            logger.error(f"Error rendering pair {pair_titles}: {str(e)}")
                            st.error(f"Error rendering images: {str(e)}")
