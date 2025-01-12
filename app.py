import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import json
from pathlib import Path
import textwrap
import emoji
from io import BytesIO
import subprocess
import os
import re
import tempfile
import uuid
from instagram_client import InstagramClient
from linkedin_client import LinkedInClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    config_path = Path(__file__).parent / 'config.json'
    with open(config_path, 'r') as f:
        return json.load(f)

def clean_text_for_image(text):
    # Remove markdown links - replace [text](url) with just text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove raw URLs with common protocols
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove other URL shorteners
    text = re.sub(r'buff\.ly/\S+', '', text)
    text = re.sub(r'bit\.ly/\S+', '', text)
    text = re.sub(r't\.co/\S+', '', text)
    
    # Remove common URL parameters
    text = re.sub(r'\?utm_[^&\s]+(&utm_[^&\s]+)*', '', text)
    text = re.sub(r'\?r=[^&\s]+', '', text)
    
    # Remove quotation marks (single and double)
    text = text.replace('"', '').replace('"', '').replace('"', '')  # Smart quotes
    text = text.replace("'", '').replace(''', '').replace(''', '')  # Smart single quotes
    text = text.replace('"', '').replace("'", '')  # Regular quotes
    
    # Remove leading hyphens at the start of sections
    text = re.sub(r'(?m)^-\s*', '', text)
    
    # Extract hashtags and put them on a new line
    main_text = []
    hashtags = []
    
    for line in text.split('\n'):
        # Find all hashtags in the line
        tags = re.findall(r'#\w+', line)
        if tags:
            # Remove the hashtags from the line
            clean_line = re.sub(r'\s*#\w+\s*', '', line).strip()
            if clean_line:  # Only add non-empty lines
                main_text.append(clean_line)
            hashtags.extend(tags)
        else:
            if line.strip():  # Only add non-empty lines
                main_text.append(line.strip())
    
    # Combine main text and hashtags
    text = '\n'.join(main_text)
    if hashtags:
        text = text + '\n\n' + ' '.join(hashtags)
    
    # Clean up any leftover artifacts
    text = re.sub(r'\s+[.!?]', '.', text)  # Fix floating punctuation
    text = re.sub(r'\s{2,}', ' ', text)    # Remove multiple spaces
    text = re.sub(r'[\n\s]*$', '', text)   # Remove trailing whitespace/newlines
    text = re.sub(r'^[\n\s]*', '', text)   # Remove leading whitespace/newlines
    
    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    
    # Remove empty parentheses that might be left after cleaning
    text = re.sub(r'\(\s*\)', '', text)
    
    return text.strip()

def parse_markdown_content(content, config=None):
    """Parse sections from markdown content string"""
    sections = {}
    current_section = None
    current_content = []
    in_collaterals = False
    header_counts = {}  # Keep track of how many times we've seen each header
    
    collaterals_header = config.get('collaterals_header', '# Collaterals') if config else '# Collaterals'

    lines = content.split('\n')
    for line in lines:
        # Start collecting at "# Collaterals"
        if line.strip() == collaterals_header:
            in_collaterals = True
            continue
        # Stop at next level 1 header
        elif line.startswith("# ") and in_collaterals:
            break
        # Process content only when we're in the Collaterals section
        elif in_collaterals:
            if line.startswith("## "):
                # Save previous section if exists
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                # Start new section with unique name
                base_section = line.lstrip("#").strip()
                if base_section in header_counts:
                    header_counts[base_section] += 1
                else:
                    header_counts[base_section] = 1
                current_section = f"{base_section} ({header_counts[base_section]})"
                current_content = []
            # Add content lines (skip other headers)
            elif current_section is not None and not line.startswith("#"):
                current_content.append(line)

    # Save the last section
    if current_section and in_collaterals:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections

def get_emoji_image(emoji_char, size):
    # Use emojirender to get colored emoji (if available on the system)
    try:
        cmd = ['emojirender', emoji_char, str(size)]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            img_data = BytesIO(result.stdout)
            return Image.open(img_data)
    except:
        pass
    
    # Fallback: try to use system emoji font
    try:
        img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype('/System/Library/Fonts/Apple Color Emoji.ttc', size)
        bbox = draw.textbbox((0, 0), emoji_char, font=font)
        x = (size - (bbox[2] - bbox[0])) // 2
        y = (size - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), emoji_char, font=font, embedded_color=True)
        return img
    except:
        return None

def create_text_image(text, width=700, height=700, font_size=40, config=None):
    def calculate_text_height(text, font_size, width, draw):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            font = ImageFont.load_default()
            
        # Calculate max chars per line
        avg_char_width = sum(draw.textlength(char, font=font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
        max_chars = int((width * 0.9) / avg_char_width)
        
        # Process text and count lines
        paragraphs = text.split('\n\n')
        total_lines = 0
        
        for paragraph in paragraphs:
            wrapped_text = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars)
            total_lines += len(wrapped_text.split('\n'))
            if len(paragraphs) > 1:
                total_lines += 1  # Add space between paragraphs
                
        line_spacing = font_size * 1.2
        return total_lines * line_spacing, font
    
    # Create a new image with alpha channel and light gray background
    image = Image.new('RGBA', (width, height), (248, 248, 248, 255))
    draw = ImageDraw.Draw(image)
    
    # Define margins and spacing
    top_margin = 40
    bottom_margin = 40
    header_height = font_size // 2 + 20 if config and config.get('header') else 0
    footer_height = font_size // 2 + 20 if config and config.get('footer') else 0
    
    # Calculate available height for main text
    available_height = height - header_height - footer_height - top_margin - bottom_margin
    
    # Find the right font size
    while font_size > 20:  # Don't go smaller than 20pt
        text_height, font = calculate_text_height(text, font_size, width, draw)
        if text_height <= available_height:
            break
        font_size -= 2
    
    # Get fonts for header/footer
    try:
        header_footer_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size // 2)
    except:
        header_footer_font = ImageFont.load_default()
    
    # Draw header if present
    if config and config.get('header'):
        header_text = config['header']
        header_width = draw.textlength(header_text, font=header_footer_font)
        header_x = (width - header_width) / 2
        header_y = top_margin // 2  # Centered in top margin
        draw.text((header_x, header_y), header_text, fill='#666666', font=header_footer_font)
    
    # Calculate maximum characters per line based on average character width
    avg_char_width = sum(draw.textlength(char, font=font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
    max_chars = int((width * 0.9) / avg_char_width)
    
    # Process the text paragraph by paragraph
    paragraphs = text.split('\n\n')
    processed_paragraphs = []
    
    for paragraph in paragraphs:
        # First wrap the text at word boundaries
        wrapped_text = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars)
        
        # Process each line for emojis
        processed_lines = []
        for line in wrapped_text.split('\n'):
            current_line = []
            current_word = ""
            
            for char in line:
                if emoji.is_emoji(char):
                    if current_word:
                        current_line.append(("text", current_word))
                        current_word = ""
                    current_line.append(("emoji", char))
                else:
                    current_word += char
            
            if current_word:
                current_line.append(("text", current_word))
            
            processed_lines.append(current_line)
        
        processed_paragraphs.extend(processed_lines)
        # Add an empty line between paragraphs
        if len(paragraphs) > 1:
            processed_paragraphs.append([])
    
    # Remove last empty line if it exists
    if processed_paragraphs and not processed_paragraphs[-1]:
        processed_paragraphs.pop()
    
    # Calculate total height and starting y position for main text
    line_spacing = font_size * 1.2
    total_height = len(processed_paragraphs) * line_spacing
    
    # Center the text between header and footer
    y = top_margin + header_height + (available_height - total_height) / 2
    
    # Draw each line
    for line in processed_paragraphs:
        if not line:  # Empty line for paragraph separation
            y += line_spacing
            continue
            
        # Calculate line width for centering
        line_width = sum(
            draw.textlength(word + " ", font=font) if word_type == "text"
            else font_size * 1.2  # emoji width
            for word_type, word in line
        )
        x = (width - line_width) / 2
        
        # Draw each word/emoji in the line
        for word_type, word in line:
            if word_type == "text":
                draw.text((x, y), word + " ", fill='black', font=font)
                x += draw.textlength(word + " ", font=font)
            else:  # emoji
                emoji_img = get_emoji_image(word, font_size)
                if emoji_img:
                    # Paste emoji with transparency
                    image.paste(emoji_img, (int(x), int(y)), emoji_img)
                x += font_size * 1.2
        
        y += line_spacing
    
    # Draw footer if present
    if config and config.get('footer'):
        footer_text = config['footer']
        footer_width = draw.textlength(footer_text, font=header_footer_font)
        footer_x = (width - footer_width) / 2
        footer_y = height - bottom_margin - font_size // 4  # Added more space by subtracting font_size//4
        draw.text((footer_x, footer_y), footer_text, fill='#666666', font=header_footer_font)
    
    return image

def save_to_photos(image_paths):
    """Save images to Photos app using AppleScript"""
    success = True
    for path in image_paths:
        apple_script = f'''
        tell application "Photos"
            activate
            import POSIX file "{path}"
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", apple_script], check=True)
        except subprocess.CalledProcessError:
            success = False
    return success

def update_selection(title):
    """Update selection state and handle select all checkbox"""
    st.session_state.selected_images[title] = st.session_state[f"checkbox_{title}"]
    if not st.session_state[f"checkbox_{title}"] and st.session_state.select_all:
        st.session_state.select_all = False

def main():
    st.set_page_config(layout="wide")  # Use wide layout for better spacing
    
    # Add custom CSS for image background
    st.markdown("""
        <style>
        .stImage img {
            background-color: #f5f5f5;
            padding: 8px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Title in main area
    st.title("Social Media Collateral Images")
    
    # Initialize session state
    if 'selected_images' not in st.session_state:
        st.session_state.selected_images = {}
    if 'select_all' not in st.session_state:
        st.session_state.select_all = False
    
    # Load configuration
    config = load_config()
    
    # Create social media clients
    instagram = InstagramClient(config)
    linkedin = LinkedInClient(config)
    
    # Add file uploader
    uploaded_file = st.file_uploader("Choose a markdown file", type=['md'], help="Upload a markdown file with sections to process")
    
    # Create a sidebar for controls
    with st.sidebar:
        st.markdown("### Controls")
        
        # Show current file being processed
        if uploaded_file:
            st.info(f"Processing uploaded file: {uploaded_file.name}")
        else:
            vault_path = Path(config['obsidian_vault_path'])
            input_filename = Path(config['input_file_path']).stem
            collateral_files = list(vault_path.glob(f"{input_filename}-collaterals*.md"))
            if collateral_files:
                latest_file = max(collateral_files, key=lambda x: x.stat().st_mtime)
                st.info(f"Processing file: {latest_file.name}")
                st.caption(f"Full path: {latest_file}")
            else:
                st.warning("No collateral files found")
        
        # Add select all checkbox in sidebar (always visible)
        if st.checkbox("Select All Images", key="select_all_checkbox", value=st.session_state.select_all):
            st.session_state.select_all = True
            for title in st.session_state.selected_images:
                st.session_state.selected_images[title] = True
        else:
            if st.session_state.select_all:
                st.session_state.select_all = False
        
        col1, col2, col3 = st.columns(3)
        
        # Add save button to first column
        with col1:
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
    
    # Find the latest collaterals file from config if no file is uploaded
    if uploaded_file is None:
        vault_path = Path(config['obsidian_vault_path'])
        input_filename = Path(config['input_file_path']).stem
        collateral_files = list(vault_path.glob(f"{input_filename}-collaterals*.md"))
        
        if not collateral_files:
            st.error("No collateral files found in vault")
            return
        
        latest_file = max(collateral_files, key=lambda x: x.stat().st_mtime)
        with open(latest_file, 'r') as f:
            content = f.read()
    else:
        content = uploaded_file.getvalue().decode('utf-8')
    
    # Parse markdown content
    sections = parse_markdown_content(content, config)
    
    # Add social media buttons to sidebar
    with st.sidebar:
        # Add Instagram post button to second column
        with col2:
            if st.button("Post to Instagram"):
                selected_items = [(title, sections[title], path) 
                                for title, path in st.session_state.get('temp_image_paths', [])
                                if st.session_state.selected_images.get(title, False)
                                and title in sections]
                
                if not selected_items:
                    st.warning("Please select at least one image first.")
                else:
                    if instagram.mock_mode:
                        st.info("Running in mock mode (no Instagram credentials). Here's what would happen:")
                        for title, content, path in selected_items:
                            # Combine header and content for caption
                            cleaned_content = clean_text_for_image(content)
                            header = config.get('header', '')
                            caption = f"{header}\n\n{cleaned_content}" if header else cleaned_content
                            
                            container_id = instagram.create_container(path, caption)
                            st.success(f"Would create post for '{title}' with caption:\n\n{caption}")
                    else:
                        if not config['instagram']['access_token']:
                            st.error("Please configure Instagram credentials in config.json")
                        else:
                            for title, content, path in selected_items:
                                # Combine header and content for caption
                                cleaned_content = clean_text_for_image(content)
                                header = config.get('header', '')
                                caption = f"{header}\n\n{cleaned_content}" if header else cleaned_content
                                
                                container_id = instagram.create_container(path, caption)
                                
                                if container_id:
                                    if instagram.test_mode:
                                        st.success(f"Test mode: Created draft post for '{title}'")
                                    else:
                                        if instagram.publish_container(container_id):
                                            st.success(f"Posted '{title}' to Instagram!")
                                        else:
                                            st.error(f"Failed to publish '{title}' to Instagram")
                                else:
                                    st.error(f"Failed to create container for '{title}'")
        
        # Add LinkedIn post button to third column
        with col3:
            if st.button("Post to LinkedIn"):
                selected_items = [(title, sections[title], path) 
                                for title, path in st.session_state.get('temp_image_paths', [])
                                if st.session_state.selected_images.get(title, False)
                                and title in sections]
                
                if not selected_items:
                    st.warning("Please select at least one image first.")
                else:
                    if linkedin.mock_mode:
                        st.info("Running in mock mode (no LinkedIn credentials). Here's what would happen:")
                        for title, content, path in selected_items:
                            # Combine header and content for text
                            cleaned_content = clean_text_for_image(content)
                            header = config.get('header', '')
                            text = f"{header}\n\n{cleaned_content}" if header else cleaned_content
                            
                            post_id = linkedin.create_post(path, text)
                            st.success(f"Would create LinkedIn post for '{title}' with text:\n\n{text}")
                    else:
                        if not config['linkedin']['access_token']:
                            st.error("Please configure LinkedIn credentials in config.json")
                        else:
                            for title, content, path in selected_items:
                                # Combine header and content for text
                                cleaned_content = clean_text_for_image(content)
                                header = config.get('header', '')
                                text = f"{header}\n\n{cleaned_content}" if header else cleaned_content
                                
                                post_id = linkedin.create_post(path, text)
                                if post_id:
                                    if linkedin.test_mode:
                                        st.success(f"Test mode: Created draft post for '{title}'")
                                    else:
                                        st.success(f"Posted '{title}' to LinkedIn!")
                                else:
                                    st.error(f"Failed to create LinkedIn post for '{title}'")
    
    if not sections:
        st.error("No sections found in the markdown file. Make sure to use '### ' to mark section headers.")
        return
    
    # Process images in pairs
    sections_items = list(sections.items())
    temp_image_paths = []
    
    for i in range(0, len(sections_items), 2):
        # Create a row for each pair of images
        col1, col2 = st.columns(2)
        
        # Process first image in the pair
        title, content = sections_items[i]
        if content.strip():
            with col1:
                st.subheader(title)
                # Clean the text before creating the image
                cleaned_content = clean_text_for_image(content)
                image = create_text_image(cleaned_content, config=config)
                
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
            title, content = sections_items[i + 1]
            if content.strip():
                with col2:
                    st.subheader(title)
                    # Clean the text before creating the image
                    cleaned_content = clean_text_for_image(content)
                    image = create_text_image(cleaned_content, config=config)
                    
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
        
        st.markdown("---")
    
    # Store temp_image_paths in session state for the sidebar button
    st.session_state.temp_image_paths = temp_image_paths
    
    # Cleanup temporary files when the app is closed
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
    main()
