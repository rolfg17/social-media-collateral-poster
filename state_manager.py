import streamlit as st
import logging

logger = logging.getLogger(__name__)

class AppState:
    """Centralized state management for the application."""
    
    def __init__(self):
        """Initialize the application state with default values."""
        self.images = {}
        self.selected_images = {}
        self.cleaned_contents = {}
        self.import_results = []
        self.select_all = False
        self.show_header_footer = True
        self.drive_authenticated = False
        self.exported_files = set()
        
    def sync_with_session(self):
        """Synchronize the state with Streamlit's session state."""
        for key, value in self.__dict__.items():
            if key not in st.session_state:
                logger.debug(f"Initializing session state for {key}")
                st.session_state[key] = value
            else:
                logger.debug(f"Loading {key} from session state")
                self.__dict__[key] = st.session_state[key]
                
    def update(self, **kwargs):
        """Update state and session state together.
        
        Args:
            **kwargs: Key-value pairs to update in both states
        """
        for key, value in kwargs.items():
            if key not in self.__dict__:
                logger.warning(f"Attempting to update unknown state key: {key}")
                continue
            logger.debug(f"Updating state for {key}")
            self.__dict__[key] = value
            st.session_state[key] = value
            
    def get(self, key, default=None):
        """Get a value from the state.
        
        Args:
            key: The key to get
            default: Default value if key doesn't exist
            
        Returns:
            The value from state or default
        """
        return self.__dict__.get(key, default)
