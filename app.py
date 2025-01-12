import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json
from pathlib import Path
import textwrap
import emoji
import subprocess
import os
import re
import tempfile
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
    
    # Remove double quotes only (including smart quotes)
    text = text.replace('"', '').replace('"', '').replace('"', '')  # Smart and regular double quotes
    
    # Remove leading hyphens at the start of sections
    text = re.sub(r'(?m)^-\s*', '', text)
    
    # Normalize spacing in numbered lists (but preserve numbers)
    text = re.sub(r'(?m)^(\d+\.)\s+', r'\1 ', text)  # Ensure single space after number
    
    # Extract hashtags and put them on a new line
    main_text = []
    hashtags = []
    
    # First pass: collect all hashtags and clean the text
    for line in text.split('\n'):
        # Find all hashtags in the line (including those with hyphens and underscores)
        tags = re.findall(r'#[a-zA-Z0-9_\-]+(?![a-zA-Z0-9_\-])', line)
        
        # Process the line
        if tags:
            hashtags.extend(tags)
            # Remove the hashtags from the line, preserving spacing
            clean_line = line
            for tag in tags:
                clean_line = clean_line.replace(tag, '')
            
            # Clean up any leftover whitespace and add non-empty lines
            clean_line = ' '.join(clean_line.split())
            if clean_line:
                main_text.append(clean_line)
        else:
            if line.strip():
                main_text.append(line.strip())
    
    # Join main text with proper line breaks
    text = '\n'.join(line for line in main_text if line.strip())
    
    # Add hashtags on a new line with proper spacing
    if hashtags:
        # Ensure there's a blank line before hashtags by adding two newlines
        text = text.rstrip() + '\n\n' + ' '.join(sorted(set(hashtags)))
    
    # Clean up any leftover artifacts
    text = re.sub(r'\s+[.!?]', '.', text)  # Fix floating punctuation
    text = re.sub(r' {2,}', ' ', text)     # Remove multiple spaces but not newlines
    text = re.sub(r'[\n\s]*$', '', text)   # Remove trailing whitespace/newlines
    text = re.sub(r'^[\n\s]*', '', text)   # Remove leading whitespace/newlines
    
    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    
    # Remove empty parentheses that might be left after cleaning
    text = re.sub(r'\(\s*\)', '', text)
    
    # Ensure proper spacing between paragraphs
    text = re.sub(r'\n{3,}', '\n\n', text)  # Replace multiple newlines with double newlines
    
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
            # Use selected body font
            font = ImageFont.truetype(st.session_state.body_font_path, font_size)
        except:
            try:
                # Fallback to Helvetica if selected font is not available
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
    
    # Create a new image with a white background
    img = Image.new('RGB', (width, height), (248, 248, 248))
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        # Header/footer font size is 60% of body text, but minimum 16pt
        header_font_size = max(int(font_size * 0.6), 16)
        header_font = ImageFont.truetype(st.session_state.header_font_path, header_font_size)
        body_font = ImageFont.truetype(st.session_state.body_font_path, font_size)
    except:
        try:
            header_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", header_font_size)
            body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            header_font = body_font = ImageFont.load_default()

    # Get header and footer from config
    header = config.get('header', '') if config else ''
    footer = config.get('footer', '') if config else ''

    # Calculate positions
    margin = height * 0.05  # 5% margin for both header and footer
    
    if header:
        header_bbox = draw.textbbox((0, 0), header, font=header_font)
        header_height = header_bbox[3] - header_bbox[1]
        header_width = draw.textlength(header, font=header_font)
        header_x = (width - header_width) // 2
        header_y = margin  # 5% from top
        draw.text((header_x, header_y), header, font=header_font, fill='#444444')
        start_y = header_y + header_height + margin  # Add margin padding
    else:
        start_y = margin * 2  # Double margin if no header

    # Calculate footer position and height
    if footer:
        footer_bbox = draw.textbbox((0, 0), footer, font=header_font)
        footer_height = footer_bbox[3] - footer_bbox[1]
        footer_width = draw.textlength(footer, font=header_font)
        footer_x = (width - footer_width) // 2
        footer_y = height - margin - footer_height  # 5% from bottom
        end_y = footer_y - margin  # Add margin padding
        draw.text((footer_x, footer_y), footer, font=header_font, fill='#444444')
    else:
        end_y = height - (margin * 2)  # Double margin if no footer

    # Calculate available height for main text
    available_height = end_y - start_y

    # Find the right font size
    while font_size > 20:  # Don't go smaller than 20pt
        text_height, font = calculate_text_height(text, font_size, width, draw)
        if text_height <= available_height:
            break
        font_size -= 2
    
    # Calculate maximum characters per line based on average character width
    avg_char_width = sum(draw.textlength(char, font=font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
    max_chars = int((width * 0.9) / avg_char_width)
    
    # Process the text paragraph by paragraph
    paragraphs = text.split('\n\n')
    processed_paragraphs = []
    
    for paragraph in paragraphs:
        # Check if this is a list (contains numbered items)
        if re.search(r'^\d+\.', paragraph, re.MULTILINE):
            # For lists, preserve line breaks
            lines = paragraph.split('\n')
            for line in lines:
                # Process each line for emojis
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
                
                processed_paragraphs.append(current_line)
        else:
            # For regular paragraphs, wrap text normally
            wrapped_text = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars)
            
            # Process each line for emojis
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
                
                processed_paragraphs.append(current_line)
        
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
    y = start_y + (available_height - total_height) / 2
    
    # Draw each line
    for line in processed_paragraphs:
        if not line:  # Empty line for paragraph separation
            y += line_spacing
            continue
            
        # Calculate x position to center this line
        line_width = sum(
            draw.textlength(word + " ", font=body_font) if word_type == "text"
            else font_size * 1.2  # emoji width
            for word_type, word in line
        )
        x = (width - line_width) / 2
        
        # Draw each word/emoji in the line
        for word_type, word in line:
            if word_type == "text":
                draw.text((x, y), word + " ", fill='black', font=body_font)
                x += draw.textlength(word + " ", font=body_font)
            else:  # emoji
                emoji_img = get_emoji_image(word, font_size)
                if emoji_img:
                    # Paste emoji with transparency
                    img.paste(emoji_img, (int(x), int(y)), emoji_img)
                x += font_size * 1.2
        
        y += line_spacing
    
    return img

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
    st.set_page_config(page_title="Social Media Collateral Generator", layout="wide")
    
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Initialize session state
    if 'selected_images' not in st.session_state:
        st.session_state.selected_images = {}
    if 'select_all' not in st.session_state:
        st.session_state.select_all = False
    
    # Title in main area
    st.title("Social Media Collateral Images")
    
    # Add file uploader
    uploaded_file = st.file_uploader("Choose a markdown file", type=['md'], help="Upload a markdown file with sections to process")
    
    # Sidebar
    st.sidebar.title("Settings")
    
    # Create a sidebar for controls
    with st.sidebar:
        
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
    
    # Create a copy of config to avoid modifying the original
    image_config = config.copy()
    
    # Update config with header override if provided
    if header_override:
        image_config['header'] = header_override
    
    # Load configuration
    config = load_config()
    
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
    
    if not sections:
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
    
    # Process images in pairs
    sections_items = [(title, content) for title, content in sections.items() if content.strip()]
    temp_image_paths = []
    
    for i in range(0, len(sections_items), 2):
        # Create a row for each pair of images
        col1, col2 = st.columns(2)
        
        # Process first image in the pair
        title, content = sections_items[i]
        with col1:
            st.subheader(title)
            # Clean the text before creating the image
            cleaned_content = clean_text_for_image(content)
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
            title, content = sections_items[i + 1]
            with col2:
                st.subheader(title)
                # Clean the text before creating the image
                cleaned_content = clean_text_for_image(content)
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
