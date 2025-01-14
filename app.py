import streamlit as st
from pathlib import Path
import subprocess
import os
import tempfile
import logging
# from dotenv import load_dotenv
from image_processor import create_text_image, validate_config, load_font  # Import from image_processor
from config_manager import load_config
from text_processor import parse_markdown_content, clean_text_for_image

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_to_photos(image_paths):
    """Save images to Photos app using AppleScript"""
    success = True
    results = []
    
    for path in image_paths:
        if not Path(path).exists():
            logger.error(f"Image file not found: {path}")
            results.append(f"❌ Failed: File not found - {path}")
            success = False
            continue
            
        apple_script = f'''
        tell application "Photos"
            activate
            delay 1
            try
                import POSIX file "{path}"
                return "Success"
            on error errMsg
                return "Error: " & errMsg
            end try
        end tell
        '''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", apple_script], 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully imported {path}")
                results.append(f"✅ Success: {path}")
            else:
                logger.error(f"Error importing {path}: {result.stderr}")
                results.append(f"❌ Failed: {result.stderr} - {path}")
                success = False
        except Exception as e:
            logger.error(f"Exception while importing {path}: {str(e)}")
            results.append(f"❌ Failed: {str(e)} - {path}")
            success = False
    
    # Show results in Streamlit
    if results:
        st.session_state.import_results = results
        st.experimental_rerun()
            
    return success

def update_selection(title):
    """Update selection state and handle select all checkbox"""
    st.session_state.selected_images[title] = st.session_state[f"checkbox_{title}"]
    if not st.session_state[f"checkbox_{title}"] and st.session_state.select_all:
        st.session_state.select_all = False

def handle_file_upload(uploaded_file, config):
    """Handle file upload and collateral generation"""
    try:
        # Read the content
        content = uploaded_file.read().decode()
        
        # Check if this is a newsletter file (has # Prompt section)
        if "# Prompt" in content:
            with st.spinner("Generating collaterals from newsletter..."):
                from collateral_generator import process_and_save_collaterals, save_to_vault
                try:
                    # Generate collaterals
                    collateral_content = process_and_save_collaterals(content, config)
                    
                    # Save to vault
                    vault_path = config['obsidian_vault_path']
                    saved_path = save_to_vault(
                        collateral_content, 
                        uploaded_file.name, 
                        vault_path
                    )
                    
                    # Create Obsidian URL
                    # Convert the absolute path to a relative vault path
                    vault_path = Path(vault_path)
                    relative_path = saved_path.relative_to(vault_path)
                    obsidian_url = f"obsidian://open?vault={vault_path.name}&file={relative_path}"
                    
                    # Show success message with link
                    st.markdown(
                        f"✅ Successfully generated and saved collaterals to: "
                        f'<a href="{obsidian_url}" target="_blank">{saved_path.name}</a>', 
                        unsafe_allow_html=True
                    )
                    
                    # Return the generated content for image processing
                    return collateral_content
                    
                except Exception as e:
                    st.error(f"Error generating collaterals: {str(e)}")
                    return None
        elif "# Collaterals" in content:
            # This is already a collaterals file, return it directly
            return content
        else:
            st.error("File must contain either '# Prompt' or '# Collaterals' section")
            return None
        
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def main():
    # Load configuration
    config = load_config()
    if not validate_config(config):
        st.error("Invalid configuration")
        return

    st.set_page_config(page_title="Social Media Collateral Generator", layout="wide")
    
    # Initialize session state
    if 'selected_images' not in st.session_state:
        st.session_state.selected_images = {}
    if 'select_all' not in st.session_state:
        st.session_state.select_all = False
    if 'import_results' not in st.session_state:
        st.session_state.import_results = None
    
    # Initialize fonts in session state
    if 'header_font_path' not in st.session_state:
        st.session_state.header_font_path = config['fonts']['paths']['Montserrat Light']
    if 'body_font_path' not in st.session_state:
        st.session_state.body_font_path = config['fonts']['paths']['FiraSans Regular']
    
    # Load fonts using image_processor's load_font function
    if 'header_font' not in st.session_state:
        st.session_state.header_font = load_font(st.session_state.header_font_path, 40)  # Default size
    if 'body_font' not in st.session_state:
        st.session_state.body_font = load_font(st.session_state.body_font_path, 40)  # Default size
    
    # Title in main area
    st.title("Social Media Collateral Images")
    
    # # Add file uploader with updated help text
    # uploaded_file = st.file_uploader(
    #     "Choose a markdown file", 
    #     type=['md'], 
    #     help="Upload either a newsletter file with a # Prompt section or a pre-generated collaterals file"
    # )
    
    # Status area for import results
    if st.session_state.import_results:
        with st.expander("Export Results", expanded=True):
            success_count = sum(1 for result in st.session_state.import_results if result.startswith('✅'))
            failure_count = len(st.session_state.import_results) - success_count
            st.write(f"✅ {success_count} successful exports, ❌ {failure_count} failed exports")
        
            # Add a button to clear the results
            if st.button("Clear Results"):
                st.session_state.import_results = None
                st.experimental_rerun()
    
    # Sidebars
    st.sidebar.title("Settings")
    
    # Create a sidebar for controls
    with st.sidebar:

        # Add file uploader with updated help text
        uploaded_file = st.file_uploader(
            "Choose a markdown file", 
            type=['md'], 
            help="Upload either a newsletter file with a # Prompt section or a pre-generated collaterals file"
        )

        # Add select all checkbox in sidebar (always visible)
        if st.checkbox("Select All Images", key="select_all_checkbox", value=st.session_state.select_all):
            st.session_state.select_all = True
            for title in st.session_state.selected_images:
                st.session_state.selected_images[title] = True
        else:
            if st.session_state.select_all:
                st.session_state.select_all = False
        
        # Add save button
        if st.button("Save to Photos"):
            selected_paths = [path for title, path in st.session_state.get('temp_image_paths', [])
                            if st.session_state.selected_images.get(title, False)]
            
            if not selected_paths:
                st.warning("Please select at least one image first.")
            else:
                if save_to_photos(selected_paths):
                    st.success(f"Successfully saved {len(selected_paths)} image(s) to Photos!")
                else:
                    st.error("Failed to save images to Photos. Please make sure Photos app is accessible.")
        
        # Add header override setting
        st.sidebar.subheader("Header Settings")
        header_override = st.sidebar.text_input("Override Header", value="", help="Leave empty to use header from config")
        
        # Font settings in sidebar
        st.sidebar.subheader("Font Settings")
        
        # Get font configurations from config
        font_paths = config['fonts']['paths']
        header_fonts = config['fonts']['header_fonts']
        body_fonts = config['fonts']['body_fonts']
        
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
        st.session_state.header_font = load_font(st.session_state.header_font_path, 40)  # Default size
        st.session_state.body_font = load_font(st.session_state.body_font_path, 40)  # Default size
    
    # Create a copy of config to avoid modifying the original
    image_config = config.copy()
    
    # Update config with header override if provided
    if header_override:
        image_config['header'] = header_override
    
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
            content = handle_file_upload(current_file, image_config)
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
                    # Use cached cleaned content
                    cleaned_content = cleaned_contents[title]
                    image = create_text_image(cleaned_content, config=image_config)
                    
                    # Save image to temporary file
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        image.save(tmp.name)
                        temp_image_paths.append((title, tmp.name))
                    
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
                            on_change=update_selection,
                            args=(title,),
                            label_visibility="collapsed"
                        )
                    
                    # Image
                    with img_col:
                        st.image(tmp.name, use_column_width=True)
                    
                    # Show the cleaned text for debugging
                    with st.expander("Show cleaned text"):
                        st.text_area("Cleaned text", cleaned_content, height=150, label_visibility="collapsed")
                
                # Process second image in the pair (if it exists)
                if i + 1 < len(sections_items):
                    title, _ = sections_items[i + 1]
                    with col2:
                        st.subheader(title)
                        # Use cached cleaned content
                        cleaned_content = cleaned_contents[title]
                        image = create_text_image(cleaned_content, config=image_config)
                        
                        # Save image to temporary file
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            image.save(tmp.name)
                            temp_image_paths.append((title, tmp.name))
                        
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
                                on_change=update_selection,
                                args=(title,),
                                label_visibility="collapsed"
                            )
                        
                        # Image
                        with img_col:
                            st.image(tmp.name, use_column_width=True)
                        
                        # Show the cleaned text for debugging
                        with st.expander("Show cleaned text"):
                            st.text_area("Cleaned text", cleaned_content, height=150, label_visibility="collapsed")
            
            # Store temporary image paths in session state
            st.session_state.temp_image_paths = temp_image_paths
            
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
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
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
                    # Create a mock uploaded file
                    from types import SimpleNamespace
                    mock_file = SimpleNamespace(
                        name=file_path.name,
                        read=lambda: content.encode('utf-8')
                    )
                    st.session_state.file_uploader = mock_file
                    logger.info("File loaded into session state")
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
