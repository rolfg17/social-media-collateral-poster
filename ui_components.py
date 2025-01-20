import streamlit as st
import logging
from typing import Dict, Set, Any, Optional
from pathlib import Path
import uuid
import os
import subprocess
from state_manager import AppState, UIState, ImageGridState, ConfigurationState, HeaderSettingsState, FileUploaderState, MainContentState, PhotosState, DriveState, ExportOptionsState
from image_processor import ImageProcessor
from config_manager import Config
from typing import TYPE_CHECKING
from file_processor import FileProcessor

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
    """Handles image grid UI components."""
    
    def __init__(self, state: AppState, app: 'App'):
        """Initialize image grid UI.
        
        Args:
            state: Application state manager
            app: Main application instance
        """
        super().__init__(state)
        self.app = app
        self.ui_state = UIState(state)
        self.grid_state = ImageGridState(self.ui_state, state)
        
    def render(self):
        """Render image grid UI components."""
        st.header("Generated Images")
        
        # Get images from session state
        grid_images = st.session_state.get('grid_images', {})
        logger.info(f"Rendering grid with images: {list(grid_images.keys())}")
        
        if not grid_images:
            st.info("No images generated yet")
            return
            
        # Create grid layout
        cols = st.columns(3)
        for i, (title, image) in enumerate(grid_images.items()):
            if image is not None:  # Only display valid images
                with cols[i % 3]:
                    try:
                        # Display image with caption
                        st.image(image, use_column_width=True, caption=title)
                        
                        # Add checkbox for selection
                        checkbox_key = f"select_{title}_{i}"  # Make key unique
                        selected = st.checkbox(
                            "Select",
                            key=checkbox_key,
                            value=self.grid_state.get_selected_images().get(title, False)
                        )
                        
                        # Update selection state if changed
                        if selected != self.grid_state.get_selected_images().get(title, False):
                            self.grid_state.select_image(title, selected)
                            
                    except Exception as e:
                        logger.error(f"Error displaying image {title}: {str(e)}")
                        st.error(f"Error displaying image {title}")
            else:
                logger.warning(f"Skipping invalid image for title: {title}")

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
        self.ui_state = UIState(state)
        self.config_state = ConfigurationState(self.ui_state, state)
        
    def render(self):
        """Render configuration UI components."""
        st.sidebar.subheader("Configuration")
        
        # Select all checkbox
        select_all = st.sidebar.checkbox(
            "Select All Images",
            value=self.config_state.get_select_all()
        )
        if select_all != self.config_state.get_select_all():
            self.config_state.set_select_all(select_all)
            
        # Show header/footer checkbox
        show_header_footer = st.sidebar.checkbox(
            "Show Header/Footer",
            value=self.config_state.get_show_header_footer()
        )
        if show_header_footer != self.config_state.get_show_header_footer():
            self.config_state.set_show_header_footer(show_header_footer)

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
        self.ui_state = UIState(state)
        self.header_state = HeaderSettingsState(self.ui_state, state)
        
    def render(self):
        """Render header settings UI components."""
        st.sidebar.subheader("Header Settings")
        
        # Header override input
        header_override = st.sidebar.text_area(
            "Header Override",
            value=self.header_state.get_header_override()
        )
        if header_override != self.header_state.get_header_override():
            self.header_state.set_header_override(header_override)
            
        # Font path inputs
        header_font = st.sidebar.text_input(
            "Header Font Path",
            value=self.header_state.get_header_font_path()
        )
        if header_font != self.header_state.get_header_font_path():
            self.header_state.set_header_font_path(header_font)
            
        body_font = st.sidebar.text_input(
            "Body Font Path",
            value=self.header_state.get_body_font_path()
        )
        if body_font != self.header_state.get_body_font_path():
            self.header_state.set_body_font_path(body_font)

class ExportOptionsUI(BaseUI):
    """Handles export options UI components."""
    
    def __init__(self, state: AppState, app: 'App'):
        """Initialize export options UI.
        
        Args:
            state: Application state manager
            app: Main application instance
        """
        super().__init__(state)
        self.app = app
        self.ui_state = UIState(state)
        self.export_state = ExportOptionsState(self.ui_state, state)
        
    def render(self):
        """Render export options UI components."""
        st.header("Export Options")
        
        # Get selected images
        selected_images = self.export_state.get_selected_images()
        if not selected_images:
            st.info("No images selected for export")
            return
            
        # Photos export
        if st.button("Save to Photos"):
            self.app.photos_ui.save_to_photos(selected_images)
            
        # Drive export
        if st.button("Export to Drive"):
            self.app.drive_ui.export_to_drive(selected_images)

class FileUploaderUI(BaseUI):
    """Handles file upload UI components."""
    
    def __init__(self, state: AppState, file_processor: FileProcessor, app: 'App'):
        """Initialize file uploader UI.
        
        Args:
            state: Application state manager
            file_processor: File processor instance
            app: Main application instance
        """
        super().__init__(state)
        self.file_processor = file_processor
        self.app = app
        self.ui_state = UIState(state)
        self.uploader_state = FileUploaderState(self.ui_state, state)
        
    def render(self):
        """Render file uploader UI components."""
        st.header("File Upload")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Upload files",
            type=["md"],
            accept_multiple_files=True,
            key="file_uploader"
        )
        
        # Show upload status
        status = self.uploader_state.get_upload_status()
        if status:
            st.info(status)
            
        # Show any errors
        error = self.uploader_state.get_upload_error()
        if error:
            st.error(error)
        
        # Handle file upload when files are present and haven't been processed
        if uploaded_files and 'last_processed_files' in st.session_state:
            last_processed = st.session_state.get('last_processed_files', set())
            current_files = {f.name for f in uploaded_files}
            
            if current_files != last_processed:
                self._handle_file_upload(uploaded_files)
                st.session_state.last_processed_files = current_files
        elif uploaded_files:
            self._handle_file_upload(uploaded_files)
            st.session_state.last_processed_files = {f.name for f in uploaded_files}
            
    def _handle_file_upload(self, uploaded_files):
        """Handle file upload process.
        
        Args:
            uploaded_files: List of uploaded files
        """
        try:
            # Process each file
            for file in uploaded_files:
                logger.info(f"Processing file: {file.name}")
                self.uploader_state.set_upload_status(f"Processing {file.name}...")
                
                # Process file
                processed_file = self.file_processor.process_file(file)
                logger.info(f"File processed: {processed_file is not None}")
                self.uploader_state.set_processed_file(processed_file)
                
                # Generate images
                if processed_file:
                    logger.info(f"Cleaned contents: {list(processed_file['cleaned_contents'].keys())}")
                    
                    # Get existing images
                    grid_images = st.session_state.get('grid_images', {}).copy()
                    logger.info(f"Existing images: {list(grid_images.keys())}")
                    
                    # Add new images
                    for title, text in processed_file['cleaned_contents'].items():
                        logger.info(f"Creating image for: {title}")
                        # Create image
                        image = self.app.image_processor.create_text_image(
                            text,
                            show_header_footer=self.state.get('show_header_footer', True)
                        )
                        logger.info(f"Image created: {image is not None}")
                        if image is not None:
                            grid_images[title] = image
                            logger.info(f"Added image to grid: {title}")
                    
                    # Update session state
                    st.session_state['grid_images'] = grid_images
                    logger.info(f"Updated session state with images: {list(grid_images.keys())}")
                
                # Add to uploaded files
                uploaded = self.uploader_state.get_uploaded_files()
                if file.name not in uploaded:
                    uploaded.append(file.name)
                    self.uploader_state.set_uploaded_files(uploaded)
            
            self.uploader_state.set_upload_status("Files processed successfully!")
            self.uploader_state.set_upload_error("")
            
        except Exception as e:
            logger.error(f"Error in _handle_file_upload: {str(e)}", exc_info=True)
            self.uploader_state.set_upload_error(str(e))
            self.uploader_state.set_upload_status("Error processing files")

class MainContentUI(BaseUI):
    """Handles main content UI components."""
    
    def __init__(self, state: AppState, app: 'App'):
        """Initialize main content UI.
        
        Args:
            state: Application state manager
            app: Main application instance
        """
        super().__init__(state)
        self.app = app
        self.ui_state = UIState(state)
        self.main_content_state = MainContentState(self.ui_state, state)
        
    def render(self):
        """Render main content UI components."""
        st.header("Content")
        
        # Display content sections
        sections = self.main_content_state.get_sections()
        if sections:
            st.write("Content sections:")
            for section in sections:
                st.write(section)
        
        # Display cleaned content
        cleaned_content = self.main_content_state.get_cleaned_contents()
        if cleaned_content:
            st.write("Cleaned content:")
            st.write(cleaned_content)

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
        self.ui_state = UIState(state)
        self.photos_state = PhotosState(self.ui_state, state)
        
    def render(self):
        """Render photos UI components."""
        if not self.photos_state.get_processed_file():
            return
            
        image_path = self.photos_state.get_image_path()
        if not image_path or not os.path.exists(image_path):
            return
            
        if st.button("Save to Photos"):
            if self.app.save_to_photos(image_path):
                st.success("Successfully saved to Photos!")
            else:
                st.error("Failed to save to Photos. Please try again.")

    def save_to_photos(self, titles: list):
        """Save images to Photos app using AppleScript.
        
        Args:
            titles: List of image titles to save
            
        Returns:
            list: List of results for each save operation
        """
        results = []
        
        for title in titles:
            try:
                # Get source file info
                source_file = (self.ui_state.get_file_uploader() or 
                             self.ui_state.get_processed_file())
                if not source_file:
                    logger.error("No source file found")
                    continue
                
                # Get image path
                image_path = self.app.get_image_path(title)
                if not image_path or not os.path.exists(image_path):
                    logger.error(f"Image not found: {image_path}")
                    continue
                
                # Save to Photos
                logger.info(f"Saving image to Photos: {image_path}")
                result = self.app.save_to_photos(image_path)
                results.append({
                    'title': title,
                    'success': result,
                    'error': None if result else "Failed to save to Photos"
                })
                
            except Exception as e:
                logger.error(f"Error saving {title} to Photos: {str(e)}")
                results.append({
                    'title': title,
                    'success': False,
                    'error': str(e)
                })
                
        # Update import results
        self.ui_state.set_import_results(results)
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
        self.ui_state = UIState(state)
        self.drive_state = DriveState(self.ui_state, state)
        
    def render(self):
        """Render drive UI components."""
        if not self.drive_state.is_authenticated():
            if st.button("Authenticate with Google Drive"):
                if self.app.authenticate_drive():
                    self.drive_state.set_authenticated(True)
                    st.success("Successfully authenticated with Google Drive!")
                else:
                    st.error("Failed to authenticate with Google Drive. Please try again.")
            return
        
        # If authenticated, show export button
        if st.button("Export to Drive"):
            if self.app.export_to_drive():
                st.success("Successfully exported to Drive!")
            else:
                st.error("Failed to export to Drive. Please try again.")
        
    def export_to_drive(self, titles):
        """Export selected images to Google Drive.
        
        Args:
            titles: List of image titles to export
            
        Returns:
            bool: True if all exports were successful
        """
        results = []
        success = True
        
        for title in titles:
            try:
                # Get source file info
                source_file = (self.ui_state.get_file_uploader() or 
                             self.ui_state.get_processed_file())
                if not source_file:
                    logger.error("No source file found")
                    continue
                
                # Get image path
                image_path = self.app.get_image_path(title)
                if not image_path or not os.path.exists(image_path):
                    logger.error(f"Image not found: {image_path}")
                    continue
                
                # Export to Drive
                logger.info(f"Exporting image to Drive: {image_path}")
                result = self.app.export_to_drive(image_path)
                
                if result:
                    results.append({
                        'title': title,
                        'success': True,
                        'error': None
                    })
                else:
                    success = False
                    results.append({
                        'title': title,
                        'success': False,
                        'error': "Failed to export to Drive"
                    })
                    
            except Exception as e:
                success = False
                logger.error(f"Error exporting {title} to Drive: {str(e)}")
                results.append({
                    'title': title,
                    'success': False,
                    'error': str(e)
                })
                
        # Update import results
        self.ui_state.set_import_results(results)
        return success
