import streamlit as st
import logging
from typing import Dict, Set, Any, Optional, Type, Union
from dataclasses import dataclass, field
from PIL import Image
import json
from datetime import datetime
import traceback
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class StateChangeLogger:
    """Logs and tracks state changes for debugging and monitoring."""
    
    def __init__(self):
        self.changes = []
        self._max_changes = 1000  # Keep last 1000 changes
        
    def log_change(self, operation: str, key: str, old_value: Any, new_value: Any, source: str):
        """Log a state change with metadata.
        
        Args:
            operation: Type of change (set, update, sync)
            key: State key being modified
            old_value: Previous value
            new_value: New value
            source: Source of the change (e.g., 'AppState', 'SessionState')
        """
        try:
            # Create change record
            change = {
                'timestamp': datetime.now().isoformat(),
                'operation': operation,
                'key': key,
                'old_value': self._safe_serialize(old_value),
                'new_value': self._safe_serialize(new_value),
                'source': source,
                'stack_trace': self._get_caller_info()
            }
            
            # Add to changes list
            self.changes.append(change)
            
            # Trim if too many changes
            if len(self.changes) > self._max_changes:
                self.changes = self.changes[-self._max_changes:]
            
            # Log the change
            logger.debug(
                f"State Change: {operation} | {key} | {source}\n"
                f"Old: {change['old_value']}\n"
                f"New: {change['new_value']}\n"
                f"Caller: {change['stack_trace']}"
            )
            
        except Exception as e:
            logger.error(f"Error logging state change: {e}")
            
    def _safe_serialize(self, value: Any) -> str:
        """Safely serialize value to string, handling non-JSON-serializable types."""
        try:
            if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                return json.dumps(value)
            return str(value)
        except Exception:
            return str(value)
            
    def _get_caller_info(self) -> str:
        """Get information about the caller from the stack trace."""
        stack = traceback.extract_stack()
        # Skip the last 3 frames (this method, log_change, and the decorator)
        relevant_frame = stack[-4]
        return f"{relevant_frame.filename}:{relevant_frame.lineno} in {relevant_frame.name}"
        
    def get_changes(self, limit: Optional[int] = None) -> list:
        """Get recent state changes.
        
        Args:
            limit: Optional limit on number of changes to return
            
        Returns:
            List of recent state changes
        """
        if limit:
            return self.changes[-limit:]
        return self.changes.copy()
        
    def clear(self):
        """Clear change history."""
        self.changes = []

def log_state_change(operation: str):
    """Decorator to log state changes.
    
    Args:
        operation: Type of operation being performed
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get old state for changed keys
            old_values = {}
            if operation == 'update':
                old_values = {k: self._state.get(k) for k in kwargs if k in self._state}
            elif operation == 'set' and len(args) >= 2:
                key = args[0]
                old_values = {key: self._state.get(key)}
            
            # Execute the operation
            result = func(self, *args, **kwargs)
            
            # Log changes
            try:
                if operation == 'update':
                    for key, new_value in kwargs.items():
                        if key in self._state:
                            self._state_logger.log_change(
                                operation, 
                                key,
                                old_values.get(key),
                                self._state.get(key),
                                'AppState'
                            )
                elif operation == 'set' and len(args) >= 2:
                    key, new_value = args[0], args[1]
                    self._state_logger.log_change(
                        operation,
                        key,
                        old_values.get(key),
                        self._state.get(key),
                        'AppState'
                    )
            except Exception as e:
                logger.error(f"Error in state change logging: {e}")
                
            return result
        return wrapper
    return decorator

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

@dataclass
class StateSchema:
    """Schema for state validation."""
    type: Type
    required: bool = True
    default: Any = None
    
    def __post_init__(self):
        """Initialize default value based on type."""
        if self.default is None and not self.required:
            if self.type in (dict, Dict):
                self.default = {}
            elif self.type == list:
                self.default = []
            elif self.type == set:
                self.default = set()
            elif self.type == str:
                self.default = ''
            elif self.type == bool:
                self.default = False
                
    def validate(self, value: Any) -> bool:
        """Validate a value against this schema."""
        if value is None:
            if self.required:
                return False
            return True
            
        # Special case for Any
        if self.type == Any:
            return True
            
        # Handle Optional types
        if getattr(self.type, "__origin__", None) == Union:
            if type(None) in self.type.__args__:
                if value is None:
                    return True
                valid_types = [t for t in self.type.__args__ if t != type(None)]
                return any(self._validate_type(value, t) for t in valid_types)
                
        return self._validate_type(value, self.type)
        
    def _validate_type(self, value: Any, type_: Type) -> bool:
        """Validate a value against a type."""
        # Handle generic types
        origin = getattr(type_, "__origin__", None)
        if origin is not None:
            if origin in (dict, Dict):
                if not isinstance(value, dict):
                    return False
                # Could add key/value type validation here
                return True
            elif origin in (list, List):
                return isinstance(value, list)
            elif origin in (set, Set):
                return isinstance(value, set)
                
        # Handle Any type
        if type_ == Any:
            return True
            
        return isinstance(value, type_)
        
class StateValidator:
    """Validates state against schema.
    
    IMPORTANT: When adding new state fields:
    1. Add them to SCHEMA with appropriate type and default value
    2. Update all relevant state categories that use the field
    3. Add tests for the new field in test_state_manager.py
    """
    
    # Schema for state validation
    SCHEMA = {
        # MAINTENANCE: Keep this schema in sync with StateRegistry dataclass
        'images': StateSchema(Dict[str, Any], default={}),
        'selected_images': StateSchema(Dict[str, bool], default={}),  
        'show_header_footer': StateSchema(bool, default=True),
        'select_all': StateSchema(bool, default=False),
        'uploaded_files': StateSchema(list, default=[]),
        'upload_status': StateSchema(str, default=''),
        'upload_error': StateSchema(str, default=''),
        'processed_file': StateSchema(Optional[Any], required=False),
        'image_path': StateSchema(str, required=False, default=''),
        'sections': StateSchema(Dict[str, Any], default={}),  
        'cleaned_contents': StateSchema(Dict[str, str], default={}),
        'header_override': StateSchema(str, default=''),
        'header_font_path': StateSchema(str, required=False, default=''),
        'body_font_path': StateSchema(str, required=False, default=''),
        'is_authenticated': StateSchema(bool, default=False),
        'drive_authenticated': StateSchema(bool, default=False),
        'test_key': StateSchema(str, required=False),  # For testing
        'test_dict': StateSchema(dict, required=False, default={})  # For testing
    }
    
    @classmethod
    def validate_type(cls, key: str, value: Any) -> bool:
        """Validate type of a state value."""
        if key not in cls.SCHEMA:
            raise ValueError(f"Unknown state key: {key}")
            
        schema = cls.SCHEMA[key]
        if not schema.validate(value):
            raise ValueError(f"Invalid type for {key}: expected {schema.type}, got {type(value)}")
            
        return True
        
    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> bool:
        """Validate entire state."""
        try:
            # Check all required keys are present
            for key, schema in cls.SCHEMA.items():
                if schema.required and key not in state:
                    raise ValueError(f"Missing required state key: {key}")
                    
            # Validate types of all present keys
            for key, value in state.items():
                if key in cls.SCHEMA:  # Only validate known keys
                    cls.validate_type(key, value)
                    
            return True
        except Exception as e:
            logger.error(f"Error validating state: {str(e)}")
            return False
            
    @classmethod
    def get_default_state(cls) -> Dict[str, Any]:
        """Get default state dict."""
        return {
            key: schema.default
            for key, schema in cls.SCHEMA.items()
            if schema.default is not None
        }

class AppState:
    """Manages application state.
    
    IMPORTANT: This class maintains synchronization between internal state and Streamlit's session_state.
    When modifying state:
    1. Always use set() or update() methods, never modify _state directly
    2. Always validate state changes through StateValidator
    3. Ensure changes are properly synced with session_state
    """
    
    def __init__(self):
        """Initialize application state with defaults."""
        # Initialize registry first
        self._registry = {}
        
        # Initialize state logger
        self._state_logger = StateChangeLogger()
        
        # Initialize state with defaults
        self._state = StateValidator.get_default_state()
        
        # Initialize from session state if it exists
        self._init_from_session_state()
        
    @log_state_change('set')
    def set(self, key: str, value):
        """Set value for key."""
        StateValidator.validate_type(key, value)
        self._state[key] = value
        # Sync with session state
        self._persist_to_session_state()
        
    @log_state_change('update')
    def update(self, **kwargs):
        """Update multiple state values.
        
        Args:
            **kwargs: State updates
            
        Raises:
            ValueError: If any value has an invalid type for a known key
        """
        # Validate all values first for known keys
        valid_updates = {}
        for key, value in kwargs.items():
            if key in self._state:
                StateValidator.validate_type(key, value)
                valid_updates[key] = value
            
        # Then update all at once
        for key, value in valid_updates.items():
            if isinstance(self._state[key], dict) and isinstance(value, dict):
                self._state[key].update(value)
            else:
                self._state[key] = value
                
        # Sync with session state
        self._persist_to_session_state()
                
    def _persist_to_session_state(self):
        """Persist current state to session state."""
        st.session_state['app_state'] = self._state.copy()
        
    def get_state_changes(self, limit: Optional[int] = None) -> list:
        """Get recent state changes.
        
        Args:
            limit: Optional limit on number of changes to return
            
        Returns:
            List of recent state changes
        """
        return self._state_logger.get_changes(limit)
        
    def clear_change_history(self):
        """Clear state change history."""
        self._state_logger.clear()
        
    def _init_from_session_state(self):
        """Initialize state from session state if it exists.
        
        IMPORTANT: This method is called during initialization to restore state after browser refreshes.
        When modifying this method:
        1. Ensure proper validation of stored state
        2. Handle invalid stored values gracefully
        3. Log any state recovery issues for debugging
        """
        if 'app_state' in st.session_state:
            try:
                stored_state = st.session_state['app_state']
                if isinstance(stored_state, dict):
                    # Validate and merge stored state
                    for key, value in stored_state.items():
                        if key in self._state:
                            try:
                                StateValidator.validate_type(key, value)
                                self._state[key] = value
                            except ValueError:
                                logger.warning(f"Invalid stored value for {key}, using default")
            except Exception as e:
                logger.error(f"Error loading stored state: {e}")
                
    def sync_with_session(self):
        """Synchronize state with Streamlit session state.
        
        IMPORTANT: This method handles bi-directional sync between AppState and session_state.
        When modifying this method:
        1. Maintain atomicity - either all changes succeed or none do
        2. Validate all values before applying changes
        3. Handle sync failures gracefully with proper error recovery
        4. Keep the sync logic in sync with _persist_to_session_state()
        """
        try:
            # First sync from session state to app state
            for key in self._state:
                if key in st.session_state:
                    try:
                        value = st.session_state[key]
                        StateValidator.validate_type(key, value)
                        if isinstance(self._state[key], dict) and isinstance(value, dict):
                            # Deep merge for dictionaries
                            self._state[key].update(value)
                        else:
                            self._state[key] = value
                    except ValueError:
                        logger.warning(f"Invalid session state value for {key}, keeping current value")
            
            # Then ensure session state has all our state
            for key, value in self._state.items():
                if key not in st.session_state or st.session_state[key] != value:
                    st.session_state[key] = value
                    
            # Persist full state
            self._persist_to_session_state()
            
        except Exception as e:
            logger.error(f"Error during state sync: {e}")
            # Try to recover by re-initializing from defaults
            self._state = StateValidator.get_default_state()
            self._persist_to_session_state()
    
    def get(self, key: str, default=None):
        """Get value for key."""
        # First check internal state
        if key in self._state:
            return self._state[key]
        # Then check registry
        if key in self._registry:
            return self._registry[key]
        return default
        
    def has(self, key: str) -> bool:
        """Check if key exists in state."""
        return key in self._state or key in self._registry
        
    def register(self, category: str, instance: Any) -> None:
        """Register a state category instance."""
        self._registry[category] = instance
        
    def get_category(self, category: str) -> Any:
        """Get a registered state category instance."""
        return self._registry.get(category)
        
    def __getattr__(self, name: str) -> Any:
        """Get attribute from state or registry."""
        # First check internal state
        if name in self._state:
            return self._state[name]
        # Then check registry
        if name in self._registry:
            return self._registry[name]
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
    
    def get_state(self) -> dict:
        """Get current state as dictionary.
        
        Returns:
            dict: Current application state
        """
        return {
            key: getattr(self, key, getattr(self._registry, key)) 
            for key in StateValidator.SCHEMA
        }
    
    def clear(self):
        """Reset state to default values."""
        self._registry = {}
    
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

class StateCategory:
    """Base class for state categories.
    
    IMPORTANT: When creating new state categories:
    1. Always inherit from this class
    2. Use the provided state_manager for all state operations
    3. Never access Streamlit's session_state directly
    4. Add appropriate tests in test_state_manager.py
    """
    
    def __init__(self, state_manager):
        """Initialize state category.
        
        Args:
            state_manager: The main state manager instance
        """
        self.state = state_manager

class UIState(StateCategory):
    """Manages UI state."""
    
    def __init__(self, app_state: AppState):
        """Initialize UI state.
        
        Args:
            app_state: Application state
        """
        super().__init__(app_state)
        self.app = app_state
        
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
        self.app.set('processed_file', file)
        
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

class ImageGridState(StateCategory):
    """Manages state for image grid UI."""
    
    def __init__(self, ui_state: UIState, app_state: AppState):
        """Initialize image grid state.
        
        Args:
            ui_state: UI state instance
            app_state: Application state instance
        """
        super().__init__(app_state)
        self.ui = ui_state
        self.app = app_state
        
    def get_images(self) -> Dict[str, Any]:
        """Get current images.
        
        Returns:
            Dict[str, Any]: Current images
        """
        return self.app.get('images', {})
        
    def set_images(self, images: Dict[str, Any]):
        """Set current images.
        
        Args:
            images: Images to set
            
        Raises:
            ValueError: If images is not a dictionary
        """
        if not isinstance(images, dict):
            raise ValueError("Images must be a dictionary")
        self.app.set('images', images)
        
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
        self.app.set('selected_images', {})
        self.app.sync_with_session()

class HeaderSettingsState(StateCategory):
    """State interface for HeaderSettings component."""
    
    def __init__(self, ui_state: UIState, app_state: AppState):
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
    
    def __init__(self, ui_state: UIState, app_state: AppState):
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
    
    def __init__(self, ui_state: UIState, app_state: AppState):
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
        return self.app.get('show_header_footer', True)
        
    def set_show_header_footer(self, value: bool) -> None:
        """Set show header/footer checkbox state.
        
        Args:
            value: New checkbox state
        """
        logger.debug(f"Setting show_header_footer to: {value}")
        self.app.update(show_header_footer=value)
        
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
    
    def __init__(self, ui_state: UIState, app_state: AppState):
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
        self.app.set('processed_file', content)  # Use set instead of update

class PhotosState(StateCategory):
    """Manages state for Photos app integration."""
    
    def __init__(self, ui_state: UIState, app_state: AppState):
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
    
    def __init__(self, ui_state: UIState, app_state: AppState):
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
    
    def __init__(self, ui_state: UIState, app_state: AppState):
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
