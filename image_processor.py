from PIL import Image, ImageDraw, ImageFont
import textwrap
import emoji
import logging
from pathlib import Path
import streamlit as st
from typing import Tuple, List, Optional, Dict


# Constants
DEFAULT_BACKGROUND_COLOR = (248, 248, 248)
DEFAULT_TEXT_COLOR = 'black'
LINE_SPACING_FACTOR = 1.3
EMOJI_WIDTH_FACTOR = 1.2
MIN_FONT_SIZE = 24
HEADER_FONT_SCALE = 0.6
MIN_HEADER_FONT_SIZE = 16
FALLBACK_SYSTEM_FONT = "/System/Library/Fonts/Helvetica.ttc"
EMOJI_FONT_PATH = "/System/Library/Fonts/Apple Color Emoji.ttc"
FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"

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

def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font with error handling."""
    try:
        size = max(MIN_FONT_SIZE, int(size))  
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        logger.error(f"Error loading font {font_path} with size {size}: {e}")
        # Return a default font as fallback
        try:
            return ImageFont.load_default()
        except Exception as fallback_e:
            logger.error(f"Failed to load default font: {fallback_e}")
            raise

def load_emoji_font(size: int) -> Optional[ImageFont.FreeTypeFont]:
    """Load emoji font with multiple fallback attempts."""
    size = max(MIN_FONT_SIZE, int(size))
    emoji_fonts = [
        EMOJI_FONT_PATH,
        "/System/Library/Fonts/AppleColorEmoji.ttf",  # Try alternate path
        "/System/Library/Fonts/Apple Color Emoji.ttf"  # Another common path
    ]
    
    # Try different sizes from largest to smallest
    sizes_to_try = [size, int(size * 0.9), int(size * 0.8), int(size * 0.7)]
    
    for font_path in emoji_fonts:
        for try_size in sizes_to_try:
            try:
                font = ImageFont.truetype(font_path, try_size)
                logger.info(f" Successfully loaded emoji font {font_path} at size {try_size}")
                return font
            except Exception as e:
                logger.debug(f"Failed to load emoji font {font_path} at size {try_size}: {e}")
                continue
    
    logger.warning(f"Failed to load any emoji font, falling back to regular font")
    return None

def process_text_line(text: str, font_size: int, max_width: int, text_color: str, background_color: Optional[str] = None) -> Image.Image:
    """Process a line of text, handling both regular text and emojis."""
    # Create initial image with generous height
    height = int(font_size * 1.5)  # Give enough vertical space
    img = Image.new('RGBA', (max_width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        font_size = max(MIN_FONT_SIZE, int(font_size))
        regular_font = load_font(st.session_state.body_font_path, font_size)
        emoji_font = load_emoji_font(font_size)
        logger.info(f"Process text line - loaded body font: {st.session_state.body_font_path}")
    except OSError as e:
        logger.error(f"Failed to load fonts: {e}")
        return img

    x = 0  # Current x position
    y = 0  # Current y position
    line_height = 0  # Track maximum height of the line

    # Process each character
    i = 0
    while i < len(text):
        char = text[i]
        
        # Check for compound emojis (like flags or skin tone modifiers)
        next_char = text[i + 1] if i + 1 < len(text) else None
        compound_emoji = None
        if next_char and emoji.is_emoji(char + next_char):
            compound_emoji = char + next_char
        
        # Determine if current character(s) is emoji
        current_text = compound_emoji if compound_emoji else char
        is_emoji = emoji.is_emoji(current_text)
        
        # Choose appropriate font
        current_font = emoji_font if is_emoji and emoji_font else regular_font
        
        # Get text size
        try:
            bbox = draw.textbbox((x, y), current_text, font=current_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception as e:
            logger.warning(f"Failed to get text size for '{current_text}': {e}")
            text_width = font_size
            text_height = font_size

        # Update line height if this character is taller
        line_height = max(line_height, text_height)
        
        # Draw the character
        try:
            if is_emoji and emoji_font:
                try:
                    draw.text((x, y), current_text, font=current_font, embedded_color=True)
                except TypeError:
                    draw.text((x, y), current_text, font=current_font, fill=text_color)
            else:
                draw.text((x, y), current_text, font=current_font, fill=text_color)
        except Exception as e:
            logger.warning(f"Failed to draw text '{current_text}': {e}")

        # Move cursor
        x += text_width
        
        # Skip extra character if we processed a compound emoji
        if compound_emoji:
            i += 2
        else:
            i += 1

    # Crop to actual content
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    
    # Create final image with proper dimensions and background
    final_height = max(line_height, img.height)
    final_img = Image.new('RGBA', (max_width, final_height), 
                         background_color if background_color else (0, 0, 0, 0))
    
    # Center vertically
    paste_y = (final_height - img.height) // 2
    final_img.paste(img, (0, paste_y), img)
    
    return final_img

def wrap_paragraph(paragraph: str, max_chars: int) -> List[str]:
    """Wrap a paragraph of text to fit within max_chars per line."""
    # Remove any existing newlines and wrap the text
    no_indent = textwrap.fill(paragraph.replace('\n', ' '), width=max_chars, initial_indent='', subsequent_indent='')
    return no_indent.split('\n')

def calculate_text_height(text: str, font_size: int, width: int, draw: ImageDraw.Draw) -> Tuple[float, ImageFont.FreeTypeFont]:
    """Calculate the height of text given the font size and width."""
    font = load_font(st.session_state.body_font_path, font_size)
    
    # Split into paragraphs
    paragraphs = text.split('\n\n')
    
    # Calculate total height
    total_height = 0
    line_height = font_size * 1.5
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            total_height += line_height
            continue
            
        # Get average character width
        avg_char_width = sum(draw.textlength(char, font=font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
        max_chars = int((width * 0.9) / avg_char_width)
        
        # Wrap text and count lines
        wrapped_lines = wrap_paragraph(paragraph, max_chars)
        total_height += len(wrapped_lines) * line_height
        
        # Add space between paragraphs
        if len(paragraphs) > 1:
            total_height += line_height
    
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

def draw_text_line(img: Image.Image, draw: ImageDraw.Draw, line: str, x: int, y: float, font_size: int, text_color: str) -> int:
    """Draw a line of text with mixed emoji and regular text."""
    # First calculate total width to center the line
    total_width = 0
    chars_to_render = []
    i = 0
    
    # Load fonts - ensure font size is valid
    try:
        font_size = max(MIN_FONT_SIZE, int(font_size))
        # Load fonts only once for the line - use session state body font
        regular_font = load_font(st.session_state.body_font_path, font_size)
        emoji_font = load_emoji_font(font_size)
        
        logger.info(f"Loaded fonts for line - body font: {st.session_state.body_font_path}, size: {font_size}")
    except OSError as e:
        logger.error(f"Failed to load fonts: {e}")
        return 0

    # First pass: calculate widths and prepare characters
    while i < len(line):
        char = line[i]
        next_char = line[i + 1] if i + 1 < len(line) else None
        compound_emoji = None
        
        if next_char and emoji.is_emoji(char + next_char):
            compound_emoji = char + next_char
            current_text = compound_emoji
            advance = 2
        else:
            current_text = char
            advance = 1
            
        is_emoji = emoji.is_emoji(current_text)
        current_font = emoji_font if is_emoji and emoji_font else regular_font
        
        try:
            bbox = draw.textbbox((0, 0), current_text, font=current_font)
            text_width = bbox[2] - bbox[0]
        except Exception as e:
            logger.warning(f"Failed to get text size for '{current_text}': {e}")
            text_width = font_size
            
        chars_to_render.append((current_text, text_width, is_emoji, current_font))
        total_width += text_width
        i += advance

    # Calculate starting x position to center the line
    start_x = (img.width - total_width) // 2
    current_x = start_x

    # Second pass: actually render the text
    for text, width, is_emoji, font in chars_to_render:
        try:
            if is_emoji and emoji_font:
                try:
                    draw.text((int(current_x), int(y)), text, font=font, embedded_color=True)
                except TypeError:
                    draw.text((int(current_x), int(y)), text, font=font, fill=text_color)
            else:
                draw.text((int(current_x), int(y)), text, font=font, fill=text_color)
        except Exception as e:
            logger.error(f"Failed to draw text: {e}")
        
        current_x += width

    return total_width

def create_text_image(text: str, width: int = 700, height: int = 700, font_size: int = 40, config: Optional[Dict[str, str]] = None) -> Image.Image:
    """Create image with text and optional background."""
    # Load background image or create blank image
    img = load_background_image(config, width, height)
    draw = ImageDraw.Draw(img)

    # Get header and footer from config
    header = config.get('header', '') if config else ''
    footer = config.get('footer', '') if config else ''
    
    margin = height * 0.05
    
    # Load header/footer font once for consistent sizing
    header_font_size = max(int(font_size * HEADER_FONT_SCALE), MIN_HEADER_FONT_SIZE)
    header_font = load_font(st.session_state.header_font_path, header_font_size)
    logger.info(f" Header/Footer font loaded with size {header_font_size}")
    
    if header:
        logger.info(f" Drawing header: '{header}'")
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
        logger.info(f"D rawing footer: '{footer}'")
        footer_bbox = draw.textbbox((0, 0), footer, font=header_font)  # Use same header_font
        footer_height = footer_bbox[3] - footer_bbox[1]
        footer_width = draw.textlength(footer, font=header_font)
        footer_x = (width - footer_width) // 2
        footer_y = height - margin - footer_height
        end_y = footer_y - margin
        draw.text((footer_x, footer_y), footer, font=header_font, fill='#444444')
    else:
        end_y = height - (margin * 2)

    # Only process main text if it exists
    if text.strip():
        logger.info(f" Processing main text (length: {len(text)})")
        text_height, body_font = calculate_text_height(text, font_size, width, draw)
        available_height = end_y - start_y
        
        while text_height > available_height and font_size > MIN_FONT_SIZE:
            font_size -= 2
            text_height, body_font = calculate_text_height(text, font_size, width, draw)
        
        # Calculate maximum characters per line
        avg_char_width = sum(draw.textlength(char, font=body_font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
        max_chars = int((width * 0.9) / avg_char_width)
        
        logger.info(f" ---- Text Wrapping")
        logger.info(f" Font size: {font_size}")
        logger.info(f" Max chars per line: {max_chars}")
        
        # Split text into paragraphs and wrap each one
        paragraphs = text.split('\n\n')
        processed_paragraphs = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                processed_paragraphs.append("")
                continue
                
            # For regular paragraphs, wrap text normally
            wrapped_lines = wrap_paragraph(paragraph, max_chars)
            processed_paragraphs.extend(wrapped_lines)
            
            # Add an empty line between paragraphs
            if len(paragraphs) > 1:
                processed_paragraphs.append("")
        
        if processed_paragraphs and not processed_paragraphs[-1]:
            processed_paragraphs.pop()
        
        # Calculate line spacing
        line_spacing = font_size * LINE_SPACING_FACTOR
        
        # Calculate total height of text block
        text_block_height = len(processed_paragraphs) * line_spacing
        
        # Calculate starting y position to center text block vertically
        y = start_y + (available_height - text_block_height) / 2
        
        # Draw each line
        for line in processed_paragraphs:
            if not line.strip():
                y += line_spacing
                continue
            
            logger.info(f" Drawing text line: '{line[:15]}{'...' if len(line) > 15 else ''}'")
            draw_text_line(img, draw, line, 0, y, font_size, DEFAULT_TEXT_COLOR)
            y += line_spacing
    else:
        logger.info("No main text to process")
    
    return img
