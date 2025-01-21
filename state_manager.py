import streamlit as st
import logging
from typing import Dict, Set, Any, Optional
from dataclasses import dataclass, field
from PIL import Image

logger = logging.getLogger(__name__)

@dataclass
class StateRegistry:
    """Registry of application state with type hints."""
    
    # Image processing state
    sections: Dict[str, str] = field(default_factory=dict)
    cleaned_contents: Dict[str, str] = field(default_factory=dict)
    images: Dict[str, Any] = field(default_factory=dict)
    # Selection state
    selected_images: Dict[str, str] = field(default_factory=dict)
    select_all: bool = False
    checkbox_keys: Dict[str, str] = field(default_factory=dict)  # Maps title to unique checkbox key
    # UI state
    show_header_footer: bool = True
    header_override: str = ""
    header_font_path: str = ""
    body_font_path: str = ""
    # Export state
    import_results: Dict[str, Any] = field(default_factory=dict)
    exported_files: Set[str] = field(default_factory=set)
    drive_authenticated: bool = False
    processed_file: Any = None

    def __post_init__(self):
        """Initialize default values for None fields."""
        if self.images is None:
            self.images = {}
        if self.selected_images is None:
            self.selected_images = {}
        if self.import_results is None:
            self.import_results = {}
        if self.exported_files is None:
            self.exported_files = set()

class StateCategory:
    """Base class for state categories.
    
    Each category manages a specific subset of the application state.
    """
    
    def __init__(self, state_manager):
        """Initialize state category.
        
        Args:
            state_manager: The main state manager instance
        """
        self.state = state_manager

class UIState(StateCategory):
    """Manages UI-specific state."""
    
    def get_checkbox(self, key: str) -> bool:
        """Get checkbox state by key.
        
        Args:
            key: The checkbox key
            
        Returns:
            bool: The checkbox state
        """
        checkbox_key = f"checkbox_{key}"
        if hasattr(self.state, checkbox_key):
            return getattr(self.state, checkbox_key)
        return False
        
    def get_font_path(self, key: str) -> str:
        """Get font path by key.
        
        Args:
            key: The font key (header or body)
            
        Returns:
            str: The font path
        """
        path_key = f"{key}_font_path"
        return getattr(self.state, path_key, "")
        
    def set_font_path(self, key: str, path: str) -> None:
        """Set font path by key.
        
        Args:
            key: The font key (header or body)
            path: The font path
        """
        path_key = f"{key}_font_path"
        self.state.update(**{path_key: path})
        
    def get_header_override(self) -> str:
        """Get header override text.
        
        Returns:
            str: The header override text
        """
        return getattr(self.state, "header_override", "")
        
    def set_header_override(self, text: str) -> None:
        """Set header override text.
        
        Args:
            text: The header override text
        """
        logger.info(f"[HeaderState] Setting header override to: '{text}'")
        self.state.update(header_override=text)
        
    def get_processed_file(self) -> Optional[Any]:
        """Get currently processed file.
        
        Returns:
            Optional[Any]: The processed file or None
        """
        return getattr(self.state, "processed_file", None)
        
    def set_processed_file(self, file: Any) -> None:
        """Set currently processed file.
        
        Args:
            file: The file to set as processed
        """
        self.state.update(processed_file=file)
        
    def get_import_results(self) -> Dict[str, Any]:
        """Get import results.
        
        Returns:
            Dict[str, Any]: The import results
        """
        return getattr(self.state, "import_results", {})
        
    def set_import_results(self, results: Dict[str, Any]) -> None:
        """Set import results.
        
        Args:
            results: The import results to set
        """
        self.state.update(import_results=results)
        
    def get_file_uploader(self) -> Optional[Any]:
        """Get file uploader state.
        
        Returns:
            Optional[Any]: The file uploader state or None
        """
        return getattr(self.state, "file_uploader", None)

class AppState:
    """Manages application state."""
    
    VALID_KEYS = {
        'sections', 'cleaned_contents', 'images', 'selected_images',
        'select_all', 'show_header_footer', 'header_override',
        'header_font_path', 'body_font_path', 'import_results', 
        'exported_files', 'drive_authenticated', 'checkbox_keys', 'processed_file',
        'test_dict', 'test_key', 'uploaded_files', 'upload_status', 'upload_error', 'image_path', 'grid_images'  # For testing purposes
    }
    
    def __init__(self):
        """Initialize application state."""
        # Initialize registry first to avoid recursion
        self._registry = {}
        
        # Initialize state attributes
        self.sections = {}
        self.cleaned_contents = {}
        self.images = {}
        self.selected_images = {}
        self.select_all = False
        self.show_header_footer = True
        self.header_override = ""
        self.header_font_path = ""
        self.body_font_path = ""
        self.import_results = {}
        self.exported_files = set()
        self.drive_authenticated = False
        self.checkbox_keys = {}
        self.processed_file = None
        self.test_dict = {}  # For testing purposes
        self.test_key = None  # For testing purposes
        self.uploaded_files = {}
        self.upload_status = ""
        self.upload_error = ""
        self.image_path = ""
        self.grid_images = {}  # Initialize as dict instead of list
        
        # Sync with session state
        for key in self.VALID_KEYS:
            if not hasattr(self, key):
                setattr(self, key, None)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get state attribute value.
        
        Args:
            key: Attribute name
            default: Default value if attribute doesn't exist
            
        Returns:
            Any: Attribute value or default
        """
        # First check session state
        if key in st.session_state:
            return st.session_state[key]
        # Then check our state
        return getattr(self, key, default)
        
    def set(self, key: str, value: Any):
        """Set state attribute value.
        
        Args:
            key: Attribute name
            value: Value to set
        """
        # Update both our state and session state
        setattr(self, key, value)
        st.session_state[key] = value
                
    def update(self, **kwargs) -> bool:
        """Update state attributes.
        
        Args:
            **kwargs: Keyword arguments mapping attribute names to values
            
        Returns:
            bool: True if update was successful
            
        Note:
            CRITICAL: This method MUST update both the internal state AND st.session_state
            to maintain consistency. Streamlit widgets read their values from session_state,
            so failing to update it will cause widgets to get out of sync.
            
            Example: The show_header_footer checkbox reads its value from session_state,
            so if we don't update session_state here, the checkbox will revert to its
            previous value even though our internal state changed.
        """
        try:
            # Validate keys
            for key in kwargs:
                if key not in self.VALID_KEYS:
                    raise ValueError(f"Invalid state key: {key}")
                    
            # Update attributes
            for key, value in kwargs.items():
                if isinstance(value, dict) and hasattr(self, key) and isinstance(getattr(self, key), dict):
                    # Merge dictionaries
                    current = dict(getattr(self, key))
                    current.update(value)
                    setattr(self, key, current)
                    st.session_state[key] = current
                else:
                    setattr(self, key, value)
                    st.session_state[key] = value
                logger.debug(f"Updated state - {key}: {value}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating state: {str(e)}")
            return False
            
    def register(self, category: str, instance: Any) -> None:
        """Register a state category instance.
        
        Args:
            category: Category name
            instance: Category instance
        """
        self._registry[category] = instance
        
    def get_category(self, category: str) -> Optional[Any]:
        """Get a registered state category instance.
        
        Args:
            category: Category name
            
        Returns:
            Optional[Any]: Category instance if found, None otherwise
        """
        return self._registry.get(category)
    
    def has(self, key: str) -> bool:
        """Check if a key exists in state.
        
        Args:
            key: Key to check
            
        Returns:
            bool: True if key exists, False otherwise
        """
        return hasattr(self, key)
    
    def __getattr__(self, name: str) -> Any:
        """Get state attribute from registry."""
        if hasattr(self._registry, name):
            return getattr(self._registry, name)
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
    
    def validate_state(self) -> bool:
        """Validate that the state is consistent."""
        try:
            # Get current state values
            sections = getattr(self, 'sections', {})
            cleaned_contents = getattr(self, 'cleaned_contents', {})
            
            # Log current state for debugging
            logger.debug(f"Validating state - sections: {sections}")
            logger.debug(f"Validating state - cleaned_contents: {cleaned_contents}")
            
            # Skip validation if both sections and contents are empty (initial state)
            if not sections and not cleaned_contents:
                logger.debug("Empty state is valid")
                return True
                
            # Validate sections and cleaned_contents match
            section_keys = set(sections.keys())
            content_keys = set(cleaned_contents.keys())
            
            if section_keys != content_keys:
                logger.error(f"Section keys {section_keys} don't match content keys {content_keys}")
                logger.error(f"Sections: {sections}")
                logger.error(f"Cleaned contents: {cleaned_contents}")
                return False
                
            logger.debug("State validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Error validating state: {str(e)}")
            return False
    
    def get_state(self) -> dict:
        """Get current state as dictionary.
        
        Returns:
            dict: Current application state
        """
        return {
            key: getattr(self, key, getattr(self._registry, key)) 
            for key in self.VALID_KEYS
        }
    
    def clear(self):
        """Reset state to default values."""
        self._registry = {}
    
    def sync_with_session(self):
        """Synchronize the state with Streamlit's session state.
        
        Note: In production, this syncs with st.session_state.
        In test mode, it maintains the current state.
        """
        # First sync from session state to our state
        for key in self.VALID_KEYS:
            if key in st.session_state:
                setattr(self, key, st.session_state[key])
            elif hasattr(self, key):
                # If key exists in our state but not in session state, sync it to session state
                st.session_state[key] = getattr(self, key)
            else:
                # Initialize both our state and session state
                setattr(self, key, None)
                st.session_state[key] = None

        # Ensure critical state values are initialized
        if 'cleaned_contents' not in st.session_state:
            st.session_state['cleaned_contents'] = {}
        if 'grid_images' not in st.session_state:
            st.session_state['grid_images'] = {}
        if 'show_header_footer' not in st.session_state:
            st.session_state['show_header_footer'] = True
        if 'header_override' not in st.session_state:
            st.session_state['header_override'] = ""

        # Sync our state with session state for these critical values
        self.cleaned_contents = st.session_state['cleaned_contents']
        self.grid_images = st.session_state['grid_images']
        self.show_header_footer = st.session_state['show_header_footer']
        self.header_override = st.session_state['header_override']

class ImageGridState(StateCategory):
    """Manages state for image grid UI."""
    
    def __init__(self, ui_state: 'UIState', app_state: AppState):
        """Initialize image grid state.
        
        Args:
            ui_state: UI state manager
            app_state: Application state manager
        """
        super().__init__(app_state)
        self.ui_state = ui_state
        self.app = self.state
        
    def get_images(self):
        """Get list of images to display.
        
        Returns:
            dict: Dictionary of images
        """
        return self.app.get("grid_images", {})
        
    def set_images(self, images):
        """Set list of images to display.
        
        Args:
            images: Dictionary of image paths
        """
        self.app.update(grid_images=images)
        
    def get_selected_images(self):
        """Get selected images.
        
        Returns:
            dict: Dictionary mapping image paths to selection state
        """
        return self.app.get("selected_images", {})
        
    def set_selected_images(self, selected):
        """Set selected images.
        
        Args:
            selected: Dictionary mapping image paths to selection state
        """
        self.app.update(selected_images=selected)
        
    def select_image(self, image_path: str, selected: bool = True):
        """Select or deselect an image.
        
        Args:
            image_path: Path to the image
            selected: True to select, False to deselect
        """
        current = self.get_selected_images()
        current[image_path] = selected
        self.set_selected_images(current)
        
    def clear_selections(self):
        """Clear all image selections."""
        self.state.selected_images = {}
        self.app.sync_with_session()

class HeaderSettingsState(StateCategory):
    """State interface for HeaderSettings component."""
    
    def __init__(self, ui_state: 'UIState', app_state: AppState):
        """Initialize HeaderSettings state interface.
        
        Args:
            ui_state: UI state manager
            app_state: Application state manager
        """
        super().__init__(app_state)
        self.ui_state = ui_state
        self.app = self.state
        logger.debug("HeaderSettingsState initialized")
        
    def get_header_override(self) -> str:
        """Get current header override text.
        
        Returns:
            str: Current header override text
        """
        current = self.app.get('header_override', '')
        logger.info(f"[HeaderState] Getting header override: '{current}'")
        return current
        
    def set_header_override(self, text: str) -> None:
        """Set header override text.
        
        Args:
            text: New header override text
        """
        logger.info(f"[HeaderState] Setting header override to: '{text}'")
        self.app.update(header_override=text)
        
    def get_header_font_path(self) -> str:
        """Get header font path.
        
        Returns:
            str: Current header font path
        """
        return self.ui_state.get_font_path("header")
        
    def set_header_font_path(self, path: str) -> None:
        """Set header font path.
        
        Args:
            path: New header font path
        """
        self.ui_state.set_font_path("header", path)
        
    def get_body_font_path(self) -> str:
        """Get body font path.
        
        Returns:
            str: Current body font path
        """
        return self.ui_state.get_font_path("body")
        
    def set_body_font_path(self, path: str) -> None:
        """Set body font path.
        
        Args:
            path: New body font path
        """
        self.ui_state.set_font_path("body", path)

class MainContentState(StateCategory):
    """Manages state for main content UI."""
    
    def __init__(self, ui_state: 'UIState', app_state: AppState):
        """Initialize main content state.
        
        Args:
            ui_state: UI state manager
            app_state: Application state manager
        """
        super().__init__(app_state)
        self.ui_state = ui_state
        self.app = self.state

    def get_sections(self):
        """Get content sections.
        
        Returns:
            list: List of content sections
        """
        return self.app.get("sections", [])

    def set_sections(self, sections):
        """Set content sections.
        
        Args:
            sections: List of content sections
        """
        self.app.update(sections=sections)

    def get_cleaned_contents(self) -> Dict[str, str]:
        """Get cleaned content.
        
        Returns:
            Dict[str, str]: Dictionary mapping titles to cleaned content
        """
        return self.app.get("cleaned_contents", {})
    
    def set_cleaned_contents(self, contents):
        """Set cleaned content.
        
        Args:
            contents: Dictionary mapping titles to cleaned content
        """
        self.app.update(cleaned_contents=contents)

    def get_header_override(self) -> str:
        """Get header override text.
        
        Returns:
            str: Current header override text
        """
        return self.ui_state.get_header_override()
    
    def get_header_font_path(self) -> str:
        """Get header font path.
        
        Returns:
            str: Current header font path
        """
        return self.ui_state.get_font_path("header")
    
    def get_body_font_path(self) -> str:
        """Get body font path.
        
        Returns:
            str: Current body font path
        """
        return self.ui_state.get_font_path("body")

class ConfigurationState(StateCategory):
    """Manages state for configuration UI."""
    
    def __init__(self, ui_state: 'UIState', app_state: AppState):
        """Initialize configuration state.
        
        Args:
            ui_state: UI state manager
            app_state: Application state manager
        """
        super().__init__(app_state)
        self.ui_state = ui_state
        self.app = self.state
        logger.debug("ConfigurationState initialized")
        
    def get_select_all(self) -> bool:
        """Get select all checkbox state.
        
        Returns:
            bool: True if select all is checked
        """
        return self.app.get('select_all', False)
        
    def set_select_all(self, value: bool) -> None:
        """Set select all checkbox state.
        
        Args:
            value: New checkbox state
        """
        logger.debug(f"Setting select_all to: {value}")
        self.app.update(select_all=value)
        
    def get_show_header_footer(self) -> bool:
        """Get show header/footer checkbox state.
        
        Returns:
            bool: True if show header/footer is checked
        """
        # Default to True if not in session state
        if 'show_header_footer' not in st.session_state:
            st.session_state.show_header_footer = True
            self.app.show_header_footer = True
            
        current = self.app.get('show_header_footer', True)
        logger.debug(f"Current show_header_footer state: {current}")
        return current
        
    def set_show_header_footer(self, value: bool) -> None:
        """Set show header/footer checkbox state.
        
        Args:
            value: New checkbox state
        """
        logger.debug(f"Setting show_header_footer to: {value}")
        # Update both internal state and session state
        self.app.update(show_header_footer=value)
        st.session_state.show_header_footer = value
        
    def get_header_override(self) -> str:
        """Get header override text.
        
        Returns:
            str: Current header override text
        """
        current = self.app.get('header_override', '')
        logger.info(f"[ConfigState] Getting header override: '{current}'")
        return current
        
    def set_header_override(self, text: str) -> None:
        """Set header override text.
        
        Args:
            text: New header override text
        """
        logger.info(f"[ConfigState] Setting header override to: '{text}'")
        self.app.update(header_override=text)

class FileUploaderState(StateCategory):
    """Manages state for file uploader UI."""
    
    def __init__(self, ui_state: 'UIState', app_state: AppState):
        """Initialize file uploader state.
        
        Args:
            ui_state: UI state manager
            app_state: Application state manager
        """
        super().__init__(app_state)
        self.ui_state = ui_state
        self.app = self.state
        
    def get_uploaded_files(self):
        """Get list of uploaded file names.
        
        Returns:
            list: List of uploaded file names
        """
        files = self.app.get("uploaded_files", [])
        if isinstance(files, dict):
            return list(files.keys())
        return files
        
    def set_uploaded_files(self, files):
        """Set list of uploaded file names.
        
        Args:
            files: List of uploaded file names
        """
        self.app.update(uploaded_files=files)
        
    def get_upload_status(self):
        """Get upload status message.
        
        Returns:
            str: Upload status message
        """
        return self.app.get("upload_status", "")
        
    def set_upload_status(self, status):
        """Set upload status message.
        
        Args:
            status: Upload status message
        """
        self.app.update(upload_status=status)
        
    def get_upload_error(self):
        """Get upload error message.
        
        Returns:
            str: Upload error message
        """
        return self.app.get("upload_error", "")
        
    def set_upload_error(self, error):
        """Set upload error message.
        
        Args:
            error: Upload error message
        """
        self.app.update(upload_error=error)
        
    def get_processed_file(self):
        """Get processed file content.
        
        Returns:
            str: Processed file content
        """
        return self.app.get("processed_file", "")
        
    def set_processed_file(self, content):
        """Set processed file content.
        
        Args:
            content: Processed file content
        """
        self.app.update(processed_file=content)

class PhotosState(StateCategory):
    """Manages state for Photos app integration."""
    
    def __init__(self, ui_state: 'UIState', app_state: AppState):
        """Initialize photos state.
        
        Args:
            ui_state: UI state manager
            app_state: Application state manager
        """
        super().__init__(app_state)  # Initialize base class first
        self.ui_state = ui_state
        self.app = self.state  # Alias state as app to match other classes
        
    def get_processed_file(self):
        """Get currently processed file."""
        return self.ui_state.get_processed_file()
    
    def get_image_path(self):
        """Get path to generated image."""
        return self.app.get("image_path", "")
    
    def set_image_path(self, path: str):
        """Set path to generated image.
        
        Args:
            path: Path to image file
        """
        self.app.update(image_path=path)

class DriveState(StateCategory):
    """Manages state for Google Drive integration."""
    
    def __init__(self, ui_state: 'UIState', app_state: AppState):
        """Initialize drive state.
        
        Args:
            ui_state: UI state manager
            app_state: Application state manager
        """
        super().__init__(app_state)
        self.ui_state = ui_state
        self.app = self.state

    def is_authenticated(self) -> bool:
        """Check if authenticated with Google Drive.
        
        Returns:
            bool: True if authenticated
        """
        return self.app.get("drive_authenticated", False)
    
    def set_authenticated(self, value: bool):
        """Set Google Drive authentication status.
        
        Args:
            value: Authentication status
        """
        self.app.update(drive_authenticated=value)

class ExportOptionsState(StateCategory):
    """Manages state for export options UI."""
    
    def __init__(self, ui_state: 'UIState', app_state: AppState):
        """Initialize export options state.
        
        Args:
            ui_state: UI state manager
            app_state: Application state manager
        """
        super().__init__(app_state)
        self.ui_state = ui_state
        self.app = self.state

    def get_selected_images(self):
        """Get selected images.
        
        Returns:
            list: List of selected image titles
        """
        return self.app.get("selected_images", [])
    
    def set_selected_images(self, images):
        """Set selected images.
        
        Args:
            images: List of selected image titles
        """
        self.app.update(selected_images=images)
