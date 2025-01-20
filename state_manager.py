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
    header_override: Optional[str] = None
    # Export state
    import_results: Dict[str, Any] = field(default_factory=dict)
    exported_files: Set[str] = field(default_factory=set)
    drive_authenticated: bool = False

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

class AppState:
    """Manages application state."""
    
    VALID_KEYS = {
        'sections', 'cleaned_contents', 'images', 'selected_images',
        'select_all', 'show_header_footer', 'header_override',
        'import_results', 'exported_files', 'drive_authenticated',
        'checkbox_keys'
    }
    
    def __init__(self):
        """Initialize state with defaults."""
        self._registry = StateRegistry()
        self.sections = {}
        self.cleaned_contents = {}
        self.images = {}
        self.selected_images = {}
        self.select_all = False
        self.show_header_footer = True
        self.header_override = None
        self.import_results = {}
        self.exported_files = set()
        self.drive_authenticated = False
        self.checkbox_keys = {}
        
        # Sync with session state
        for key in self.VALID_KEYS:
            if key in st.session_state:
                setattr(self, key, st.session_state[key])
                setattr(self._registry, key, st.session_state[key])
    
    def __getattr__(self, name: str) -> Any:
        """Get state attribute from registry."""
        if hasattr(self._registry, name):
            return getattr(self._registry, name)
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
    
    def update(self, **kwargs):
        """Update state with new values."""
        try:
            # Get current state snapshot
            old_state = {
                key: getattr(self, key, {})
                for key in self.VALID_KEYS
            }
            
            # Queue all updates
            updates = {}
            for key, value in kwargs.items():
                if key in self.VALID_KEYS:
                    # Ensure we have a new dictionary for mutable types
                    if isinstance(value, dict):
                        value = dict(value)  # Create a new copy
                    logger.debug(f"Queueing state update for {key}: {value}")
                    updates[key] = value
                else:
                    logger.warning(f"Skipping unknown state key: {key}")
            
            if not updates:
                logger.debug("No updates to apply")
                return True
                
            # Apply all updates atomically
            try:
                for key, value in updates.items():
                    logger.debug(f"Setting {key} = {value}")
                    # Update instance
                    setattr(self, key, value)
                    # Update registry
                    setattr(self._registry, key, value)
                    # Update session state
                    st.session_state[key] = value
                    
                # Validate new state
                if self.validate_state():
                    logger.debug("State update successful")
                    return True
                    
                # Rollback on validation failure
                logger.error("State validation failed, rolling back")
                for key, value in old_state.items():
                    setattr(self, key, value)
                    setattr(self._registry, key, value)
                    st.session_state[key] = value
                return False
                
            except Exception as e:
                logger.error(f"Error during state update: {str(e)}", exc_info=True)
                # Rollback on error
                for key, value in old_state.items():
                    setattr(self, key, value)
                    setattr(self._registry, key, value)
                    st.session_state[key] = value
                return False
                
        except Exception as e:
            logger.error(f"Error preparing state update: {str(e)}", exc_info=True)
            return False
            
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
            logger.error(f"Error validating state: {str(e)}", exc_info=True)
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
        self._registry = StateRegistry()
    
    def sync_with_session(self):
        """Synchronize the state with Streamlit's session state.
        
        Note: In production, this syncs with st.session_state.
        In test mode, it maintains the current state.
        """
        try:
            # In production mode, sync with Streamlit session state
            for key, value in self._registry.__dict__.items():
                if key not in st.session_state:
                    logger.debug(f"Initializing session state for {key}")
                    self.update(**{key: value})
                else:
                    logger.debug(f"Loading {key} from session state")
                    self.update(**{key: st.session_state[key]})
        except Exception as e:
            # In test mode or if Streamlit is not available
            logger.debug(f"Running in test mode or Streamlit not available: {str(e)}")
            # Keep current state
            pass
                
    def set(self, key, value):
        """Set a value in both instance and session state.
        
        Args:
            key: The key to set
            value: The value to set
        """
        logger.debug(f"Setting state for {key}")
        self.update(**{key: value})
        st.session_state[key] = value
        
    def has(self, key):
        """Check if a key exists in state.
        
        Args:
            key: The key to check
            
        Returns:
            bool: True if key exists, False otherwise
        """
        return hasattr(self._registry, key)
