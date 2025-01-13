from PIL import Image, ImageDraw, ImageFont
import textwrap
import emoji
import subprocess
import re
from io import BytesIO
import logging
from pathlib import Path
import streamlit as st
import sys
from datetime import datetime
from typing import Tuple, List, Optional, Dict


# Constants
DEFAULT_BACKGROUND_COLOR = (248, 248, 248)
DEFAULT_TEXT_COLOR = 'black'
LINE_SPACING_FACTOR = 1.3
EMOJI_WIDTH_FACTOR = 1.2
MIN_FONT_SIZE = 20
HEADER_FONT_SCALE = 0.6
MIN_HEADER_FONT_SIZE = 16
FALLBACK_SYSTEM_FONT = "/System/Library/Fonts/Helvetica.ttc"
EMOJI_FONT_PATH = "/System/Library/Fonts/Apple Color Emoji.ttc"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_config(config: Optional[Dict[str, str]]) -> bool:
    """Validate configuration dictionary.
    
    Returns False if config is invalid, True otherwise.
    Logs specific validation errors.
    """
    if not config:
        return True
        
    required_keys = ['background_image_path']
    for key in required_keys:
        if key in config and not isinstance(config[key], str):
            logger.error(f"Config error: {key} must be a string")
            return False
    return True

def load_font(font_path: str, font_size: int) -> ImageFont.FreeTypeFont:
    """Load a font with fallback options."""
    try:
        return ImageFont.truetype(font_path, font_size)
    except OSError as e:
        logger.warning(f"Failed to load font {font_path}: {e}")
        try:
            return ImageFont.truetype(FALLBACK_SYSTEM_FONT, font_size)
        except OSError as e:
            logger.error(f"Failed to load fallback font: {e}")
            return ImageFont.load_default()

def get_emoji_image(emoji_char: str, size: int) -> Optional[Image.Image]:
    """Convert emoji character to PIL Image."""
    # try:
    #     result = subprocess.run(['emojirender', emoji_char], capture_output=True, text=True)
    #     if result.returncode == 0:
    #         try:
    #             convert_result = subprocess.run(
    #                 ['convert', 'svg:-', 'png:-'],
    #                 input=result.stdout.encode(),
    #                 capture_output=True
    #             )
    #             if convert_result.returncode == 0:
    #                 img = Image.open(BytesIO(convert_result.stdout))
    #                 img = img.resize((size, size))
    #                 return img
    #         except (subprocess.SubprocessError, IOError) as e:
    #             logger.warning(f"Failed to convert emoji using ImageMagick: {e}")
    # except subprocess.SubprocessError as e:
    #     logger.warning(f"Failed to render emoji using emojirender: {e}")
    
    # Fallback: render emoji as text
    try:
        img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(EMOJI_FONT_PATH, size)
        bbox = draw.textbbox((0, 0), emoji_char, font=font)
        x = (size - (bbox[2] - bbox[0])) // 2
        y = (size - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), emoji_char, font=font, embedded_color=True)
        return img
    except Exception as e:
        logger.warning(f"Failed to render emoji as text: {e}")
        return None

def wrap_paragraph(paragraph: str, max_chars: int) -> List[str]:
    """Wrap a paragraph of text to fit within max_chars per line."""
    normal_wrap = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars)
    no_indent = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars, initial_indent='', subsequent_indent='')
    return no_indent.split('\n')

def process_text_line(line: str, font_size: int) -> List[Tuple[str, str]]:
    """Process a line of text, separating emojis from regular text."""
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
    
    return current_line

def calculate_text_height(text: str, font_size: int, width: int, draw: ImageDraw.Draw) -> Tuple[float, ImageFont.FreeTypeFont]:
    """Calculate the height of text given the font size and width."""
    font = load_font(st.session_state.body_font_path, font_size)
            
    # Calculate average character width using a more representative sample
    sample_text = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?"
    total_width = draw.textlength(sample_text, font=font)
    avg_char_width = total_width / len(sample_text)
    max_chars = int((width * 0.85) / avg_char_width)
    
    logger.info(f" Max chars per line: {max_chars}")
    
    paragraphs = text.split('\n\n')
    total_lines = 0
    
    for paragraph in paragraphs:
        
        # Try with different textwrap options
        normal_wrap = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars)
        no_indent = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars, initial_indent='', subsequent_indent='')
        
        wrapped_text = no_indent  # Use no_indent version for now
        total_lines += len(wrapped_text.split('\n'))
        if len(paragraphs) > 1:
            total_lines += 1
        
    # Calculate total height needed
    line_height = font.size * LINE_SPACING_FACTOR  # Add 50% line spacing
    total_height = total_lines * line_height
    
    return total_height, font

def load_background_image(config: Dict[str, str], width: int, height: int) -> Image.Image:
    """Load and resize background image from config, or create blank image."""
    if config and 'background_image_path' in config:
        bg_path = Path(__file__).parent / config['background_image_path']
        if bg_path.exists():
            try:
                bg_img = Image.open(bg_path)
                # Resize to maintain aspect ratio and cover the required dimensions
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
                
                return bg_img.convert('RGB')
            except Exception as e:
                logger.error(f"Error loading background image: {e}")
    
    return Image.new('RGB', (width, height), DEFAULT_BACKGROUND_COLOR)

def draw_text_line(img: Image.Image, draw: ImageDraw.Draw, line: List[Tuple[str, str]], x: int, y: int, body_font: ImageFont.FreeTypeFont, font_size: int) -> int:
    """Draw a line of text with mixed emoji and regular text."""
    current_x = x
    for word_type, word in line:
        if word_type == "text":
            draw.text((current_x, y), word + " ", fill=DEFAULT_TEXT_COLOR, font=body_font)
            current_x += draw.textlength(word + " ", font=body_font)
        else:  # emoji
            emoji_img = get_emoji_image(word, font_size)
            if emoji_img:
                # Paste emoji with transparency
                img.paste(emoji_img, (int(current_x), int(y)), emoji_img)
            current_x += font_size * EMOJI_WIDTH_FACTOR
    return current_x - x  # Return total width of line

def create_text_image(text: str, width: int = 700, height: int = 700, font_size: int = 40, config: Optional[Dict[str, str]] = None) -> Image.Image:
    """Create image with text and optional background."""
    if not validate_config(config):
        logger.warning("Invalid config provided, using defaults")
        config = None
    
    # Create or load background image
    img = load_background_image(config, width, height)
    draw = ImageDraw.Draw(img)

    # Load fonts
    header_font_size = max(int(font_size * HEADER_FONT_SCALE), MIN_HEADER_FONT_SIZE)
    header_font = load_font(st.session_state.header_font_path, header_font_size)
    body_font = load_font(st.session_state.body_font_path, font_size)

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
    while font_size > MIN_FONT_SIZE:
        text_height, font = calculate_text_height(text, font_size, width, draw)
        if text_height <= available_height:
            break
        font_size -= 2
    
    # Calculate maximum characters per line
    avg_char_width = sum(draw.textlength(char, font=body_font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
    max_chars = int((width * 0.9) / avg_char_width)
    
    logger.info(f" ---- Text Wrapping")
    logger.info(f" Width: {width}, Avg char width: {avg_char_width:.2f}")
    logger.info(f" Max chars per line: {max_chars}")
    
    # Process the text paragraph by paragraph
    paragraphs = text.split('\n\n')
    processed_paragraphs = []
    
    for paragraph in paragraphs:
        # For regular paragraphs, wrap text normally
        wrapped_lines = wrap_paragraph(paragraph, max_chars)
        for line in wrapped_lines:
            processed_paragraphs.append(process_text_line(line, font_size))
        
        # Add an empty line between paragraphs
        if len(paragraphs) > 1:
            processed_paragraphs.append([])
    
    if processed_paragraphs and not processed_paragraphs[-1]:
        processed_paragraphs.pop()
    
    # Calculate total height and starting y position for main text
    line_spacing = font_size * LINE_SPACING_FACTOR
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
            else font_size * EMOJI_WIDTH_FACTOR  # emoji width
            for word_type, word in line
        )
        x = (width - line_width) / 2
        
        # Draw the line
        draw_text_line(img, draw, line, x, y, body_font, font_size)
        y += line_spacing
    
    return img
