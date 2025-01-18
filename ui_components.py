import streamlit as st
import logging
import uuid

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
