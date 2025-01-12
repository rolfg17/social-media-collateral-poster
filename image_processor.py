from PIL import Image, ImageDraw, ImageFont
import textwrap
import emoji
import subprocess
from io import BytesIO
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_emoji_image(emoji_char, size):
    """Convert emoji character to PIL Image"""
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
    """Create image with text and optional background"""
    def calculate_text_height(text, font_size, width, draw):
        try:
            font = ImageFont.truetype(st.session_state.body_font_path, font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                font = ImageFont.load_default()
            
        avg_char_width = sum(draw.textlength(char, font=font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
        max_chars = int((width * 0.9) / avg_char_width)
        
        paragraphs = text.split('\n\n')
        total_lines = 0
        
        for paragraph in paragraphs:
            wrapped_text = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars)
            total_lines += len(wrapped_text.split('\n'))
            if len(paragraphs) > 1:
                total_lines += 1
                
        line_spacing = font_size * 1.2
        return total_lines * line_spacing, font

    # Create or load background image
    if config and 'background_image_path' in config:
        bg_path = Path(__file__).parent / config['background_image_path']
        if bg_path.exists():
            try:
                bg_img = Image.open(bg_path)
                bg_ratio = bg_img.width / bg_img.height
                target_ratio = width / height
                
                if bg_ratio > target_ratio:  # Image is wider than needed
                    new_width = int(height * bg_ratio)
                    bg_img = bg_img.resize((new_width, height))
                    left = (new_width - width) // 2
                    bg_img = bg_img.crop((left, 0, left + width, height))
                else:  # Image is taller than needed
                    new_height = int(width / bg_ratio)
                    bg_img = bg_img.resize((width, new_height))
                    top = (new_height - height) // 2
                    bg_img = bg_img.crop((0, top, width, top + height))
                
                img = bg_img.convert('RGB')
            except Exception as e:
                logger.error(f"Error loading background image: {e}")
                img = Image.new('RGB', (width, height), (248, 248, 248))
        else:
            img = Image.new('RGB', (width, height), (248, 248, 248))
    else:
        img = Image.new('RGB', (width, height), (248, 248, 248))
    
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
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
    margin = height * 0.05
    
    if header:
        header_bbox = draw.textbbox((0, 0), header, font=header_font)
        header_height = header_bbox[3] - header_bbox[1]
        header_width = draw.textlength(header, font=header_font)
        header_x = (width - header_width) // 2
        header_y = margin
        draw.text((header_x, header_y), header, font=header_font, fill='#444444')
        start_y = header_y + header_height + margin
    else:
        start_y = margin * 2

    if footer:
        footer_bbox = draw.textbbox((0, 0), footer, font=header_font)
        footer_height = footer_bbox[3] - footer_bbox[1]
        footer_width = draw.textlength(footer, font=header_font)
        footer_x = (width - footer_width) // 2
        footer_y = height - margin - footer_height
        end_y = footer_y - margin
        draw.text((footer_x, footer_y), footer, font=header_font, fill='#444444')
    else:
        end_y = height - (margin * 2)

    # Calculate available height for main text
    available_height = end_y - start_y

    # Find the right font size
    while font_size > 20:
        text_height, font = calculate_text_height(text, font_size, width, draw)
        if text_height <= available_height:
            break
        font_size -= 2
    
    # Calculate maximum characters per line
    avg_char_width = sum(draw.textlength(char, font=font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
    max_chars = int((width * 0.9) / avg_char_width)
    
    # Process the text paragraph by paragraph
    paragraphs = text.split('\n\n')
    processed_paragraphs = []
    
    for paragraph in paragraphs:
        if re.search(r'^\d+\.', paragraph, re.MULTILINE):
            lines = paragraph.split('\n')
            for line in lines:
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
            wrapped_text = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars)
            
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
        
        if len(paragraphs) > 1:
            processed_paragraphs.append([])
    
    if processed_paragraphs and not processed_paragraphs[-1]:
        processed_paragraphs.pop()
    
    # Calculate total height and starting y position for main text
    line_spacing = font_size * 1.2
    total_height = len(processed_paragraphs) * line_spacing
    
    # Center the text between header and footer
    y = start_y + (available_height - total_height) / 2
    
    # Draw each line
    for line in processed_paragraphs:
        if not line:
            y += line_spacing
            continue
            
        line_width = sum(
            draw.textlength(word + " ", font=body_font) if word_type == "text"
            else font_size * 1.2
            for word_type, word in line
        )
        x = (width - line_width) / 2
        
        for word_type, word in line:
            if word_type == "text":
                draw.text((x, y), word + " ", fill='black', font=body_font)
                x += draw.textlength(word + " ", font=body_font)
            else:
                emoji_img = get_emoji_image(word, font_size)
                if emoji_img:
                    img.paste(emoji_img, (int(x), int(y)), emoji_img)
                x += font_size * 1.2
        
        y += line_spacing
    
    return img
