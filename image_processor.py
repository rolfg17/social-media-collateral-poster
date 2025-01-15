from PIL import Image, ImageDraw, ImageFont
import textwrap
import emoji
import logging
from pathlib import Path
import streamlit as st
from typing import Tuple, List, Optional, Dict, Any


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
logging.basicConfig(level=logging.DEBUG)  # Change to DEBUG to see all logs
logger = logging.getLogger(__name__)

# Constants for font configuration
FONT_CONFIG = {
    'DEFAULT_TEXT_COLOR': 'black',
    'LINE_SPACING_FACTOR': 1.3,
    'EMOJI_WIDTH_FACTOR': 1.2,
    'MIN_FONT_SIZE': 24,
    'HEADER_FONT_SCALE': 0.6,
    'MIN_HEADER_FONT_SIZE': 16,
    'FALLBACK_SYSTEM_FONT': "/System/Library/Fonts/Helvetica.ttc",
    'FONT_PATH': "/System/Library/Fonts/Helvetica.ttc",
    'EMOJI_FONT_PATH': "/System/Library/Fonts/Apple Color Emoji.ttc"
}

# Common text drawing utilities
def get_font_metrics(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    """Get width and height of text with given font."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_centered_text(draw: ImageDraw.Draw, text: str, x: int, y: int, font: ImageFont.FreeTypeFont, 
                      width: int, color: str = FONT_CONFIG['DEFAULT_TEXT_COLOR']) -> None:
    """Draw text centered horizontally at given y position."""
    text_width, _ = get_font_metrics(draw, text, font)
    x = (width - text_width) // 2
    draw.text((x, y), text, font=font, fill=color)

def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font with error handling."""
    try:
        size = max(FONT_CONFIG['MIN_FONT_SIZE'], int(size))  # Ensure size is at least MIN_FONT_SIZE
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        logger.error(f"Error loading font {font_path} with size {size}: {e}")
        try:
            return ImageFont.load_default()
        except Exception as fallback_e:
            logger.error(f"Failed to load default font: {fallback_e}")
            raise

def load_emoji_font(size: int) -> Optional[ImageFont.FreeTypeFont]:
    """Load emoji font with multiple fallback attempts."""
    size = max(FONT_CONFIG['MIN_FONT_SIZE'], int(size))
    emoji_fonts = [
        EMOJI_FONT_PATH,  # Use the constant defined at the top
        "/System/Library/Fonts/Apple Color Emoji.ttc",  # Primary macOS emoji font
        "/usr/share/fonts/truetype/apple-emoji/Apple Color Emoji.ttc",  # Possible Linux location
        "/usr/share/fonts/truetype/emoji/NotoColorEmoji.ttf",  # Noto fallback
    ]
    
    # Try different sizes from largest to smallest
    sizes_to_try = [
        size,                    # 100%
        int(size * 0.9),        # 90%
        int(size * 0.8),        # 80%
        int(size * 0.7),        # 70%
        int(size * 0.6),        # 60%
        int(size * 0.5),        # 50%
        int(size * 0.4),        # 40%
        int(size * 0.3),        # 30%
        max(int(size * 0.25), FONT_CONFIG['MIN_FONT_SIZE'])  # 25% but not smaller than min font size
    ]

    logger.debug(f"Attempting to load emoji font. Paths to try: {emoji_fonts}")
    logger.debug(f"Font sizes to try: {sizes_to_try}")
    
    for font_path in emoji_fonts:
        if not Path(font_path).exists():
            logger.debug(f"Font file not found: {font_path}")
            continue
            
        logger.debug(f"Found font file: {font_path}")
        for try_size in sizes_to_try:
            try:
                font = ImageFont.truetype(font_path, try_size)
                logger.debug(f"Successfully loaded emoji font: {font_path} (size: {try_size})")
                return font
            except Exception as e:
                logger.debug(f"Failed to load {font_path} at size {try_size}: {str(e)}")
                continue
    
    logger.debug("Could not load emoji font, will fall back to regular font for emoji characters")
    return None

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

def process_text_line(text: str, font_size: int, max_width: int, text_color: str, background_color: Optional[str] = None) -> Image.Image:
    """
    Process a line of text, handling both regular text and emojis, and 
    return an image of the processed text.

    Args:
        text (str): The text to be processed.
        font_size (int): The size of the font to be used.
        max_width (int): The maximum width of the resulting image.
        text_color (str): The color of the text.
        background_color (Optional[str]): The background color of the image.

    Returns:
        Image.Image: An image containing the processed text.
    """
    # Create initial image with generous height to accommodate text
    height = int(font_size * 1.5)  # Give enough vertical space for text
    img = Image.new('RGBA', (max_width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Load fonts, handling potential errors
    try:
        font_size = max(FONT_CONFIG['MIN_FONT_SIZE'], int(font_size))
        regular_font = load_font(st.session_state.body_font_path, font_size)
        emoji_font = load_emoji_font(font_size)
        logger.info(f"Process text line - loaded body font: {st.session_state.body_font_path}")
    except OSError as e:
        logger.error(f"Failed to load fonts: {e}")
        return img

    x = 0  # Current x position for drawing text
    y = 0  # Current y position for drawing text
    line_height = 0  # Track maximum height of the current line

    i = 0
    while i < len(text):
        char = text[i]
        
        # Check for compound emojis (e.g., flags or skin tone modifiers)
        next_char = text[i + 1] if i + 1 < len(text) else None
        compound_emoji = None
        if next_char and emoji.is_emoji(char + next_char):
            compound_emoji = char + next_char
        
        # Determine if the current character(s) is an emoji
        current_text = compound_emoji if compound_emoji else char
        is_emoji = emoji.is_emoji(current_text)
        
        # Choose appropriate font based on whether it's an emoji
        current_font = emoji_font if is_emoji and emoji_font else regular_font
        
        # Get text size, with error handling
        try:
            bbox = draw.textbbox((x, y), current_text, font=current_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception as e:
            logger.warning(f"Failed to get text size for '{current_text}': {e}")
            text_width = font_size
            text_height = font_size

        # Update line height if this character has greater height
        line_height = max(line_height, text_height)
        
        # Draw the character, handling emojis differently if needed
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

        # Move cursor to the right by the width of the drawn text
        x += text_width
        
        # Skip extra character if a compound emoji was processed
        if compound_emoji:
            i += 2
        else:
            i += 1

    # Crop to actual content to remove excess space
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    
    # Create final image with proper dimensions and background color
    final_height = max(line_height, img.height)
    final_img = Image.new('RGBA', (max_width, final_height), 
                         background_color if background_color else (0, 0, 0, 0))
    
    # Center the text vertically in the final image
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
    """
    Load and resize a background image based on configuration or create a blank image if not available.
    
    The function attempts to load a background image specified in the configuration. It first tries the absolute path,
    then a path relative to the configuration file. If both attempts fail, it creates a blank image with the given dimensions.

    :param config: Configuration dictionary with an optional 'background_image_path' key.
    :param width: Width of the final image.
    :param height: Height of the final image.
    :return: An Image object of the loaded or created background.
    """
    # Check if background image path is in config
    if config and 'background_image_path' in config:
        project_root = Path(__file__).parent
        bg_path = project_root / config['background_image_path']
        
        logger.info(f"Attempting to load background image from: {bg_path}")
        
        # Attempt to load image from the specified path
        if bg_path.exists():
            try:
                bg_img = Image.open(bg_path)
                logger.info(f"Successfully loaded background image: {bg_path}")
                
                # Calculate aspect ratios
                bg_ratio = bg_img.width / bg_img.height
                target_ratio = width / height
                
                # Resize the image to maintain aspect ratio
                if bg_ratio > target_ratio:
                    new_width = int(height * bg_ratio)
                    bg_img = bg_img.resize((new_width, height))
                    left = (new_width - width) // 2
                    bg_img = bg_img.crop((left, 0, left + width, height))
                else:
                    new_height = int(width / bg_ratio)
                    bg_img = bg_img.resize((width, new_height))
                    top = (new_height - height) // 2
                    bg_img = bg_img.crop((0, top, width, top + height))
                
                return bg_img.convert('RGB')
            except Exception as e:
                logger.error(f"Error loading background image: {e}")
                logger.error(f"Attempted path: {bg_path}")
        
        else:
            logger.error(f"Background image not found at path: {bg_path}")
            # Try path relative to config file location
            config_path = project_root / 'config.json'
            if config_path.exists():
                config_dir = config_path.parent
                relative_path = config_dir / config['background_image_path']
                
                try:
                    if relative_path.exists():
                        bg_img = Image.open(relative_path)
                        logger.info(f"Successfully loaded background image from config relative path: {relative_path}")
                        
                        bg_ratio = bg_img.width / bg_img.height
                        target_ratio = width / height
                        
                        if bg_ratio > target_ratio:
                            new_width = int(height * bg_ratio)
                            bg_img = bg_img.resize((new_width, height))
                            left = (new_width - width) // 2
                            bg_img = bg_img.crop((left, 0, left + width, height))
                        else:
                            new_height = int(width / bg_ratio)
                            bg_img = bg_img.resize((width, new_height))
                            top = (new_height - height) // 2
                            bg_img = bg_img.crop((0, top, width, top + height))
                        
                        return bg_img.convert('RGB')
                except Exception as e:
                    logger.error(f"Error loading background image from config relative path: {e}")
                    logger.error(f"Attempted path: {relative_path}")
    else:
        logger.warning("No background_image_path in config, using default background")
    
    # Return a blank image with default color if no image is found
    return Image.new('RGB', (width, height), DEFAULT_BACKGROUND_COLOR)

def draw_text_line(img: Image.Image, draw: ImageDraw.Draw, line: str, x: int, y: float, font_size: int, text_color: str, emoji_font: Optional[ImageFont.FreeTypeFont] = None) -> int:
    """
    Draw a line of text with mixed emoji and regular text.

    :param img: Background image to draw the text on.
    :param draw: ImageDraw object for drawing on the image.
    :param line: Line of text to draw.
    :param x: X position of the top-left corner of the text.
    :param y: Y position of the top-left corner of the text.
    :param font_size: Font size of the text.
    :param text_color: Color of the text.
    :param emoji_font: Pre-loaded emoji font to use for emoji characters.
    :return: Width of the drawn text.
    """
    i = 0
    total_width = 0
    chars_to_render = []
    
    # Load regular font first
    try:
        font_size = max(FONT_CONFIG['MIN_FONT_SIZE'], int(font_size))
        regular_font = load_font(st.session_state.body_font_path, font_size)
        logger.info(f"Loaded fonts for line - body font: {st.session_state.body_font_path}, size: {font_size}")
    except OSError as e:
        logger.error(f"Failed to load regular font: {e}")
        return 0
    
    # Check if we need emoji font
    has_emoji = any(emoji.is_emoji(char) or (i + 1 < len(line) and emoji.is_emoji(char + line[i + 1])) 
                   for i, char in enumerate(line))
    
    emoji_font = None
    if has_emoji:
        logger.debug(f"Text contains emojis, loading emoji font: {line}")
        emoji_font = load_emoji_font(font_size)

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
        
        # Get text size, with error handling
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
            logger.error(f"Failed to render text '{text}': {e}")
        current_x += width

    return total_width

def create_text_image(text: str, width: int = 700, height: int = 700, font_size: int = 40, config: Optional[Dict[str, str]] = None) -> Image.Image:
    """
    Create an image with text and an optional background, header, and footer.

    :param text: Main text to be added to the image.
    :param width: Width of the image.
    :param height: Height of the image.
    :param font_size: Font size for the main text.
    :param config: Optional configuration dictionary for additional settings.
    :return: Image with the specified text.
    """
    if config is None:
        config = {}

    # Create image and drawing context
    img = load_background_image(config, width, height)
    draw = ImageDraw.Draw(img)

    # Retrieve header and footer from the configuration
    header = config.get('header', '') if config else ''
    footer = config.get('footer', '') if config else ''
    
    # Define margin for the image components
    margin = height * 0.05
    
    # Load the font for header/footer with appropriate size scaling
    header_font_size = max(int(font_size * FONT_CONFIG['HEADER_FONT_SCALE']), FONT_CONFIG['MIN_HEADER_FONT_SIZE'])
    header_font = load_font(st.session_state.header_font_path, header_font_size)
    logger.info(f"Header/Footer font loaded with size {header_font_size}")
    
    # Calculate and draw the header if it exists
    if header:
        logger.info(f"Drawing header: '{header}'")
        header_bbox = draw.textbbox((0, 0), header, font=header_font)
        header_height = header_bbox[3] - header_bbox[1]
        header_width = draw.textlength(header, font=header_font)
        header_x = (width - header_width) // 2
        header_y = margin
        draw_centered_text(draw, header, header_x, header_y, header_font, width)
        start_y = header_y + header_height + margin
    else:
        start_y = margin * 2
    
    # Calculate and draw the footer if it exists
    if footer:
        logger.info(f"Drawing footer: '{footer}'")
        footer_bbox = draw.textbbox((0, 0), footer, font=header_font)  # Use the same header font
        footer_height = footer_bbox[3] - footer_bbox[1]
        footer_y = height - margin - footer_height
        draw_centered_text(draw, footer, 0, footer_y, header_font, width)
        end_y = footer_y - margin
    else:
        end_y = height - (margin * 2)

    # Process the main text if it is not empty
    if text.strip():
        logger.info(f"Processing main text (length: {len(text)})")
        text_height, body_font = calculate_text_height(text, font_size, width, draw)
        available_height = end_y - start_y
        
        # Adjust font size to fit the available space
        while text_height > available_height and font_size > FONT_CONFIG['MIN_FONT_SIZE']:
            font_size -= 2
            text_height, body_font = calculate_text_height(text, font_size, width, draw)
        
        # Calculate the maximum number of characters per line
        avg_char_width = sum(draw.textlength(char, font=body_font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
        max_chars = int((width * 0.9) / avg_char_width)
        
        logger.info(f"Text Wrapping - Font size: {font_size}, Max chars per line: {max_chars}")
        
        # Split text into paragraphs and wrap each one
        paragraphs = text.split('\n\n')
        processed_paragraphs = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                processed_paragraphs.append("")
                continue
                
            wrapped_lines = wrap_paragraph(paragraph, max_chars)
            processed_paragraphs.extend(wrapped_lines)
            
            if len(paragraphs) > 1:
                processed_paragraphs.append("")
        
        if processed_paragraphs and not processed_paragraphs[-1]:
            processed_paragraphs.pop()
        
        # Calculate line spacing
        line_spacing = font_size * FONT_CONFIG['LINE_SPACING_FACTOR']
        
        # Calculate total height of text block
        text_block_height = len(processed_paragraphs) * line_spacing
        
        # Calculate starting y position to center the text block vertically
        y = start_y + (available_height - text_block_height) / 2
        
        # Draw each line of text
        for line in processed_paragraphs:
            if not line.strip():
                y += line_spacing
                continue
            
            logger.info(f"Drawing text line: '{line[:15]}{'...' if len(line) > 15 else ''}'")
            draw_text_line(img, draw, line, 0, y, font_size, FONT_CONFIG['DEFAULT_TEXT_COLOR'])
            y += line_spacing
    else:
        logger.info("No main text to process")
    
    return img

class ImageProcessor:
    """Main class for handling image processing operations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the ImageProcessor with configuration."""
        self.config = config
        self._validate_config()
        self._font_cache = {}  # Cache for loaded fonts
        self.header_font = None
        self.body_font = None
        
        # Validate emoji font availability early
        emoji_font = load_emoji_font(FONT_CONFIG['MIN_FONT_SIZE'])
        if emoji_font is None:
            logger.warning("No valid emoji font found. Emoji support may be limited.")
            
    def _validate_config(self):
        """Internal config validation."""
        if not validate_config(self.config):
            raise ValueError("Invalid configuration provided")
            
    def _get_cached_font(self, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        """Get a font from cache or load it if not cached."""
        cache_key = (font_path, size)
        if cache_key not in self._font_cache:
            self._font_cache[cache_key] = load_font(font_path, size)
        return self._font_cache[cache_key]
    
    def load_fonts(self, header_path: str, body_path: str, header_font_size: int, body_font_size: int):
        """Load header and body fonts with specified paths and sizes."""
        self.header_font = self._get_cached_font(header_path, header_font_size)
        self.body_font = self._get_cached_font(body_path, body_font_size)
        
    def get_header_font(self, size: Optional[int] = None) -> ImageFont.FreeTypeFont:
        """Get header font with optional size override."""
        if size is not None:
            return self._get_cached_font(self.config.get('header_font_path', FONT_PATH), size)
        if self.header_font is None:
            raise RuntimeError("Header font not loaded. Call load_fonts first.")
        return self.header_font
        
    def get_body_font(self, size: Optional[int] = None) -> ImageFont.FreeTypeFont:
        """Get body font with optional size override."""
        if size is not None:
            return self._get_cached_font(self.config.get('body_font_path', FONT_PATH), size)
        if self.body_font is None:
            raise RuntimeError("Body font not loaded. Call load_fonts first.")
        return self.body_font

    def create_text_image(self, text: str, config: Optional[Dict[str, Any]] = None, **kwargs) -> Image.Image:
        """Create text image with loaded fonts and optional configuration override."""
        if not (self.header_font and self.body_font):
            raise ValueError("Fonts must be loaded before creating images")
            
        # Use instance config if no override provided
        image_config = config if config is not None else self.config
        
        # Extract dimensions and font size from config
        width = image_config.get('width', 700)  # Default width
        height = image_config.get('height', 700)  # Default height
        font_size = image_config.get('font_size', 40)  # Default font size
        
        # Create image and drawing context
        img = load_background_image(image_config, width, height)
        draw = ImageDraw.Draw(img)
        
        # Get header and footer text
        header = image_config.get('header', '')
        footer = image_config.get('footer', '')
        
        # Define margin
        margin = height * 0.05
        
        # Calculate header font size and use cached font
        header_font_size = max(int(font_size * FONT_CONFIG['HEADER_FONT_SCALE']), 
                             FONT_CONFIG['MIN_HEADER_FONT_SIZE'])
        header_font = self._get_cached_font(image_config.get('header_font_path', FONT_PATH), header_font_size)
        
        # Process header if present
        start_y = margin * 2
        if header:
            logger.info(f"Drawing header: '{header}'")
            header_bbox = draw.textbbox((0, 0), header, font=header_font)
            header_height = header_bbox[3] - header_bbox[1]
            header_x = (width - draw.textlength(header, font=header_font)) // 2
            header_y = margin
            draw_centered_text(draw, header, header_x, header_y, header_font, width)
            start_y = header_y + header_height + margin
            
        # Process footer if present
        end_y = height - (margin * 2)
        if footer:
            logger.info(f"Drawing footer: '{footer}'")
            footer_bbox = draw.textbbox((0, 0), footer, font=header_font)
            footer_height = footer_bbox[3] - footer_bbox[1]
            footer_y = height - margin - footer_height
            draw_centered_text(draw, footer, 0, footer_y, header_font, width)
            end_y = footer_y - margin
            
        # Process main text
        if text.strip():
            logger.info(f"Processing main text (length: {len(text)})")
            body_font = self.get_body_font(font_size)
            
            # Calculate initial text height
            text_height = self._calculate_text_height(text, body_font, width, draw)
            available_height = end_y - start_y
            
            # Adjust font size if needed
            while text_height > available_height and font_size > FONT_CONFIG['MIN_FONT_SIZE']:
                font_size -= 2
                body_font = self.get_body_font(font_size)
                text_height = self._calculate_text_height(text, body_font, width, draw)
            
            # Calculate text wrapping
            avg_char_width = sum(draw.textlength(char, font=body_font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
            max_chars = int((width * 0.9) / avg_char_width)
            
            # Process and draw text
            y = start_y + (available_height - text_height) / 2
            
            paragraphs = text.split('\n\n')
            for paragraph in paragraphs:
                if not paragraph.strip():
                    y += body_font.size * FONT_CONFIG['LINE_SPACING_FACTOR']
                    continue
                    
                wrapped_lines = wrap_paragraph(paragraph, max_chars)
                for line in wrapped_lines:
                    if line.strip():
                        draw_text_line(img, draw, line, 0, y, font_size, DEFAULT_TEXT_COLOR, 
                                     self.get_emoji_font(font_size))
                    y += body_font.size * FONT_CONFIG['LINE_SPACING_FACTOR']
                
                # Add extra spacing between paragraphs
                y += body_font.size * (FONT_CONFIG['LINE_SPACING_FACTOR'] - 1)
        
        return img
        
    def _calculate_text_height(self, text: str, font: ImageFont.FreeTypeFont, width: int, 
                             draw: ImageDraw.Draw) -> float:
        """Calculate the total height needed for the text with the given font."""
        total_height = 0
        line_height = font.size * FONT_CONFIG['LINE_SPACING_FACTOR']
        
        # Calculate average character width for wrapping
        avg_char_width = sum(draw.textlength(char, font=font) for char in 'abcdefghijklmnopqrstuvwxyz') / 26
        max_chars = int((width * 0.9) / avg_char_width)
        
        paragraphs = text.split('\n\n')
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                total_height += line_height
                continue
                
            wrapped_lines = wrap_paragraph(paragraph, max_chars)
            total_height += len(wrapped_lines) * line_height
            
            # Add extra spacing between paragraphs (except last one)
            if i < len(paragraphs) - 1:
                total_height += font.size * (FONT_CONFIG['LINE_SPACING_FACTOR'] - 1)
        
        return total_height
        
    def get_emoji_font(self, size: int) -> Optional[ImageFont.FreeTypeFont]:
        """Get cached emoji font with the specified size. Returns None if no emoji font is available."""
        cache_key = ('emoji', size)
        if cache_key not in self._font_cache:
            self._font_cache[cache_key] = load_emoji_font(size)
        return self._font_cache[cache_key]

# Public API
__all__ = [
    'create_text_image',  # Main image creation function
    'load_font',          # Font loading utility
    'validate_config',    # Configuration validation
    'FONT_CONFIG'         # Font configuration constants
]
