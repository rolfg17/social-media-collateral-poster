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

def load_config():
    with open('config.json', 'r') as f:
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

def parse_markdown_sections(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sections = {}
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        if line.startswith('###'):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        elif line.startswith('#'):
            continue
        else:
            if current_section:
                current_content.append(line)
    
    if current_section:
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

def create_text_image(text, width=700, height=700, font_size=40):
    # Create a new image with alpha channel and light gray background
    image = Image.new('RGBA', (width, height), (245, 245, 245, 255))
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        font = ImageFont.load_default()
    
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
    
    # Calculate total height and starting y position
    line_spacing = font_size * 1.2
    total_height = len(processed_paragraphs) * line_spacing
    y = (height - total_height) / 2
    
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

def main():
    st.set_page_config(layout="wide")  # Use wide layout for better spacing
    
    # Title in main area
    st.title("Social Media Collateral Images")
    
    # Initialize session state
    if 'selected_images' not in st.session_state:
        st.session_state.selected_images = {}
    if 'select_all' not in st.session_state:
        st.session_state.select_all = False
    
    # Create a sidebar for controls
    with st.sidebar:
        st.markdown("### Controls")
        # Add select all checkbox in sidebar (always visible)
        if st.checkbox("Select All Images", key="select_all_checkbox", value=st.session_state.select_all):
            st.session_state.select_all = True
            for title in st.session_state.selected_images:
                st.session_state.selected_images[title] = True
        else:
            if st.session_state.select_all:
                st.session_state.select_all = False
        
        # Add save button to sidebar
        if st.button("Save Selected to Photos"):
            selected_paths = [path for title, path in st.session_state.get('temp_image_paths', [])
                            if st.session_state.selected_images.get(title, False)]
            
            if not selected_paths:
                st.warning("Please select at least one image first.")
            else:
                if save_to_photos(selected_paths):
                    st.success(f"Successfully saved {len(selected_paths)} image(s) to Photos!")
                else:
                    st.error("Failed to save images to Photos. Please make sure Photos app is accessible.")
    
    # Load configuration
    config = load_config()
    
    # Find the latest collaterals file
    vault_path = Path(config['obsidian_vault_path'])
    input_filename = Path(config['input_file_path']).stem
    
    collateral_files = list(vault_path.glob(f"{input_filename}-collaterals*.md"))
    if not collateral_files:
        st.error("No collateral files found. Please generate collaterals first.")
        return
    
    # Get the latest file
    latest_file = max(collateral_files, key=lambda x: x.stat().st_mtime)
    
    # Parse sections from the markdown file
    sections = parse_markdown_sections(latest_file)
    
    # Create and display images for each section
    temp_image_paths = []
    
    # Add custom CSS for image background
    st.markdown("""
        <style>
        .stImage img {
            background-color: #f5f5f5;
            padding: 8px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Process images in pairs
    sections_items = list(sections.items())
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
                image = create_text_image(cleaned_content)
                # Convert RGBA to RGB for Streamlit with light gray background
                image_rgb = Image.new('RGB', image.size, (245, 245, 245))  # #f5f5f5 in RGB
                image_rgb.paste(image, mask=image.split()[3])
                
                # Save image to temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    image_rgb.save(tmp.name)
                    temp_image_paths.append((title, tmp.name))
                
                # Create checkbox and image container
                check_col, img_col = st.columns([1, 10])
                
                # Initialize this image's state if not present
                if title not in st.session_state.selected_images:
                    st.session_state.selected_images[title] = False
                
                # Checkbox
                with check_col:
                    if st.checkbox(
                        "Select image",
                        key=f"select_{title}",
                        value=st.session_state.selected_images[title],
                        label_visibility="collapsed"
                    ):
                        st.session_state.selected_images[title] = True
                    else:
                        st.session_state.selected_images[title] = False
                        if st.session_state.select_all:
                            st.session_state.select_all = False
                
                # Image
                with img_col:
                    st.image(image_rgb, use_column_width=True)
                
                # Optionally show the cleaned text for debugging
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
                    image = create_text_image(cleaned_content)
                    # Convert RGBA to RGB for Streamlit with light gray background
                    image_rgb = Image.new('RGB', image.size, (245, 245, 245))  # #f5f5f5 in RGB
                    image_rgb.paste(image, mask=image.split()[3])
                    
                    # Save image to temporary file
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        image_rgb.save(tmp.name)
                        temp_image_paths.append((title, tmp.name))
                    
                    # Create checkbox and image container
                    check_col, img_col = st.columns([1, 10])
                    
                    # Initialize this image's state if not present
                    if title not in st.session_state.selected_images:
                        st.session_state.selected_images[title] = False
                    
                    # Checkbox
                    with check_col:
                        if st.checkbox(
                            "Select image",
                            key=f"select_{title}",
                            value=st.session_state.selected_images[title],
                            label_visibility="collapsed"
                        ):
                            st.session_state.selected_images[title] = True
                        else:
                            st.session_state.selected_images[title] = False
                            if st.session_state.select_all:
                                st.session_state.select_all = False
                    
                    # Image
                    with img_col:
                        st.image(image_rgb, use_column_width=True)
                    
                    # Optionally show the cleaned text for debugging
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
