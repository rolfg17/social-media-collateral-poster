from PIL import Image, ImageDraw, ImageFont
import textwrap
import emoji
import logging
from pathlib import Path
import streamlit as st
from typing import Tuple, List, Optional, Dict, Any
import tempfile
import os

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
logging.basicConfig(level=logging.WARNING)  # Change to WARNING to suppress detailed logs
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
    """Get width and height of text with given font.
    
    Args:
        draw: ImageDraw object for text measurements
        text: Text to measure
        font: Font to use for measurement
        
    Returns:
        Tuple[int, int]: Width and height of the text
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_centered_text(draw: ImageDraw.Draw, text: str, x: int, y: int, font: ImageFont.FreeTypeFont, 
                      width: int, color: str = FONT_CONFIG['DEFAULT_TEXT_COLOR']) -> None:
    """Draw text centered horizontally at given y position.
    
    Args:
        draw: ImageDraw object for drawing
        text: Text to draw
        x: Initial x position (will be adjusted for centering)
        y: Y position to draw at
        font: Font to use for drawing
        width: Total width available for centering
        color: Color to draw the text in
    """
    text_width, _ = get_font_metrics(draw, text, font)
    x = (width - text_width) // 2
    draw.text((x, y), text, font=font, fill=color)

def load_font(font_path: str, size: int) -> Optional[ImageFont.FreeTypeFont]:
    """Load a font with error handling.
    
    Args:
        font_path: Path to font file
        size: Font size
        
    Returns:
        Optional[ImageFont.FreeTypeFont]: Loaded font or None if loading fails
    """
    try:
        if not font_path:
            logger.error("Empty font path provided")
            return ImageFont.truetype(FALLBACK_SYSTEM_FONT, size)
            
        if not os.path.exists(font_path):
            logger.error(f"Font file not found: {font_path}")
            return ImageFont.truetype(FALLBACK_SYSTEM_FONT, size)
            
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        logger.error(f"Error loading font {font_path} with size {size}: {e}")
        try:
            return ImageFont.truetype(FALLBACK_SYSTEM_FONT, size)
        except Exception as e:
            logger.error(f"Failed to load fallback font: {e}")
            return None

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
            bbox = draw.textbbox((0, 0), current_text, font=current_font)
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
    if not config:
        # Create a blank image with alpha channel
        return Image.new('RGBA', (width, height), DEFAULT_BACKGROUND_COLOR + (255,))
        
    # Get background image path from config
    bg_path = config.get('background_image_path')
    if not bg_path:
        # Create a blank image with alpha channel
        return Image.new('RGBA', (width, height), DEFAULT_BACKGROUND_COLOR + (255,))
    
    # Try absolute path first
    if not os.path.exists(bg_path):
        logger.warning(f"Background image not found at absolute path: {bg_path}")
        # Create a blank image with alpha channel
        return Image.new('RGBA', (width, height), DEFAULT_BACKGROUND_COLOR + (255,))
    
    try:
        # Open and convert to RGBA mode for alpha channel support
        img = Image.open(bg_path).convert('RGBA')
        
        # Calculate resize dimensions preserving aspect ratio
        img_width, img_height = img.size
        aspect = img_width / img_height
        
        if width / height > aspect:
            # Image is too tall, resize based on width
            new_width = width
            new_height = int(width / aspect)
        else:
            # Image is too wide, resize based on height
            new_height = height
            new_width = int(height * aspect)
            
        # Resize with high quality
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create a new image with the target size and alpha channel
        final_img = Image.new('RGBA', (width, height), DEFAULT_BACKGROUND_COLOR + (255,))
        
        # Calculate paste position to center
        paste_x = (width - new_width) // 2
        paste_y = (height - new_height) // 2
        
        # Paste resized image onto center of canvas
        final_img.paste(img, (paste_x, paste_y))
        
        return final_img
        
    except Exception as e:
        logger.error(f"Error loading background image {bg_path}: {e}")
        # Create a blank image with alpha channel
        return Image.new('RGBA', (width, height), DEFAULT_BACKGROUND_COLOR + (255,))

class ImageProcessor:
    """Main class for handling image processing operations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the ImageProcessor with configuration."""
        self.config = config
        self._validate_config()
        self._font_cache = {}  # Cache for loaded fonts
        self._emoji_font_cache = {}  # Dedicated cache for emoji fonts
        self._background_cache = {}  # Cache for background images
        self.header_font = None
        self.body_font = None
        
        # Load fonts during initialization
        try:
            # Get font paths from config
            header_path = None
            body_path = None
            
            if 'fonts' in config:
                font_config = config['fonts']
                # Get header font path
                if font_config.get('header_fonts'):
                    header_name = font_config['header_fonts'][0]
                    header_path = font_config.get('paths', {}).get(header_name)
                
                # Get body font path
                if font_config.get('body_fonts'):
                    body_name = font_config['body_fonts'][0]
                    body_path = font_config.get('paths', {}).get(body_name)
            
            # Store font paths in session state
            st.session_state.header_font_path = header_path or "/System/Library/Fonts/Helvetica.ttc"
            st.session_state.body_font_path = body_path or "/System/Library/Fonts/Helvetica.ttc"
            
            # Load fonts with fallback
            self.load_fonts(
                header_path=st.session_state.header_font_path,
                body_path=st.session_state.body_font_path,
                header_font_size=40,
                body_font_size=40
            )
        except Exception as e:
            logger.error(f"Failed to initialize fonts: {e}")
            # Use system fallback font
            st.session_state.header_font_path = "/System/Library/Fonts/Helvetica.ttc"
            st.session_state.body_font_path = "/System/Library/Fonts/Helvetica.ttc"
            self.load_fonts(
                header_path=st.session_state.header_font_path,
                body_path=st.session_state.body_font_path,
                header_font_size=40,
                body_font_size=40
            )
            
    def load_fonts(self, header_path: str, body_path: str, header_font_size: int, body_font_size: int):
        """Load header and body fonts with specified paths and sizes."""
        try:
            # Load header font
            if not header_path or not os.path.exists(header_path):
                logger.error(f"Invalid header font path: {header_path}")
                header_path = "/System/Library/Fonts/Helvetica.ttc"
                
            # Load body font    
            if not body_path or not os.path.exists(body_path):
                logger.error(f"Invalid body font path: {body_path}")
                body_path = "/System/Library/Fonts/Helvetica.ttc"
            
            # Try to load fonts
            try:
                self.header_font = ImageFont.truetype(header_path, header_font_size)
                logger.info(f"Successfully loaded header font: {header_path}")
            except Exception as e:
                logger.error(f"Failed to load header font: {e}")
                self.header_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", header_font_size)
                
            try:
                self.body_font = ImageFont.truetype(body_path, body_font_size)
                logger.info(f"Successfully loaded body font: {body_path}")
            except Exception as e:
                logger.error(f"Failed to load body font: {e}")
                self.body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", body_font_size)
            
            # Cache the fonts
            self._font_cache[f"{header_path}_{header_font_size}"] = self.header_font
            self._font_cache[f"{body_path}_{body_font_size}"] = self.body_font
            
        except Exception as e:
            logger.error(f"Error in font loading: {e}")
            # Final fallback - use system font
            try:
                fallback = "/System/Library/Fonts/Helvetica.ttc"
                self.header_font = ImageFont.truetype(fallback, header_font_size)
                self.body_font = ImageFont.truetype(fallback, body_font_size)
                logger.info("Using system fallback font")
            except Exception as e:
                logger.error(f"Failed to load system fallback font: {e}")
                raise
            
    def _validate_config(self):
        """Internal config validation."""
        if not validate_config(self.config):
            raise ValueError("Invalid configuration provided")
            
    def _get_cached_font(self, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        """Get a font from cache or load it if not cached."""
        cache_key = f"{font_path}_{size}"
        if cache_key not in self._font_cache:
            self._font_cache[cache_key] = load_font(font_path, size)
        return self._font_cache[cache_key]

    def _get_cached_emoji_font(self, size: int) -> Optional[ImageFont.FreeTypeFont]:
        """Get emoji font from cache or load it if not cached."""
        if size not in self._emoji_font_cache:
            self._emoji_font_cache[size] = load_emoji_font(size)
        return self._emoji_font_cache[size]

    def _get_cached_background(self, config: Dict[str, str], width: int, height: int) -> Image.Image:
        """Get a background image from cache or load it if not cached."""
        cache_key = f"{config.get('background_image_path', '')}_{width}_{height}"
        if cache_key not in self._background_cache:
            self._background_cache[cache_key] = load_background_image(config, width, height)
        return self._background_cache[cache_key].copy()  # Return a copy to avoid modifying cached image

    def draw_text_line(self, img: Image.Image, draw: ImageDraw.Draw, line: str, x: int, y: float, 
                      font_size: int, text_color: str) -> int:
        """
        Draw a line of text with mixed emoji and regular text.

        :param img: Background image to draw the text on.
        :param draw: ImageDraw object for drawing on the image.
        :param line: Line of text to draw.
        :param x: X position of the top-left corner of the text.
        :param y: Y position of the top-left corner of the text.
        :param font_size: Font size of the text.
        :param text_color: Color of the text.
        :return: Width of the drawn text.
        """
        if not line:
            return 0
            
        # Get cached body font
        body_font = self._get_cached_font(st.session_state.body_font_path, font_size)
        if not body_font:
            logger.error("Failed to load body font")
            return 0
        
        # Get cached emoji font if needed
        emoji_font = None
        if any(c in emoji.EMOJI_DATA for c in line):
            emoji_font = self._get_cached_emoji_font(font_size)
        
        # Get image width
        width = img.width
        
        # If line has no emojis, use simple centered text drawing
        if not any(c in emoji.EMOJI_DATA for c in line):
            draw_centered_text(draw, line, x, y, body_font, width, text_color)
            return draw.textlength(line, font=body_font)
            
        # For lines with emojis, we need to handle them specially
        current_text = ""
        total_width = 0
        
        # First pass: calculate total width
        for char in line:
            if char in emoji.EMOJI_DATA:
                if current_text:
                    total_width += draw.textlength(current_text, font=body_font)
                    current_text = ""
                if emoji_font:
                    total_width += draw.textlength(char, font=emoji_font)
            else:
                current_text += char
        if current_text:
            total_width += draw.textlength(current_text, font=body_font)
            
        # Calculate starting x position for centering
        start_x = (width - total_width) // 2
        current_x = start_x
        current_text = ""
        
        # Second pass: draw the text
        for char in line:
            if char in emoji.EMOJI_DATA:
                if current_text:
                    text_width = draw.textlength(current_text, font=body_font)
                    draw.text((current_x, y), current_text, font=body_font, fill=text_color)
                    current_x += text_width
                    current_text = ""
                if emoji_font:
                    # Draw emoji with embedded color
                    draw.text((current_x, y), char, font=emoji_font, embedded_color=True)
                    current_x += draw.textlength(char, font=emoji_font)
            else:
                current_text += char
                
        # Draw any remaining text
        if current_text:
            draw.text((current_x, y), current_text, font=body_font, fill=text_color)
        
        return total_width

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

    def get_text_metrics(self, draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        """Get width and height from a single bbox calculation.
        
        Args:
            draw: ImageDraw object for text measurements
            text: Text to measure
            font: Font to use for measurement
        
        Returns:
            Tuple[int, int]: Width and height of the text
        """
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]  # width, height

    def get_avg_char_width(self, draw: ImageDraw.Draw, font: ImageFont.FreeTypeFont) -> float:
        """Calculate and cache average character width for a font.
        
        Args:
            draw: ImageDraw object for text measurements
            font: Font to calculate average width for
        
        Returns:
            float: Average width of lowercase letters in the font
        """
        cache_key = ('avg_width', id(font))
        if cache_key not in self._font_cache:
            # Calculate average width of lowercase letters
            self._font_cache[cache_key] = sum(draw.textlength(char, font=font) 
                                            for char in 'abcdefghijklmnopqrstuvwxyz') / 26
        return self._font_cache[cache_key]

    def create_text_image(self, text: str, config: Optional[Dict[str, Any]] = None, show_header_footer: bool = True, **kwargs) -> Image.Image:
        """Create text image with loaded fonts and optional configuration override.
        
        Args:
            text: Text to be added to the image
            config: Optional configuration dictionary for additional settings
            show_header_footer: Whether to show header and footer text (default: True)
            **kwargs: Additional keyword arguments
            
        Returns:
            Image.Image: Generated image
        """
        # Merge configurations
        image_config = self.config.copy() if self.config else {}
        if config:
            image_config.update(config)
        
        # Get image dimensions
        width = image_config.get('width', 700)
        height = image_config.get('height', 700)
        font_size = image_config.get('font_size', 40)  # Default font size
        
        # Create image and drawing context
        img = self._get_cached_background(image_config, width, height)
        draw = ImageDraw.Draw(img)
        
        # Get header and footer text
        header = image_config.get('header', '') if show_header_footer else ''
        footer = image_config.get('footer', '') if show_header_footer else ''
        
        # Define margin for the image components
        margin = height * 0.05
        
        # Calculate header font size
        header_font_size = max(int(font_size * FONT_CONFIG['HEADER_FONT_SCALE']), 
                             FONT_CONFIG['MIN_HEADER_FONT_SIZE'])
        header_font = self._get_cached_font(st.session_state.header_font_path, header_font_size)
        
        # Calculate and draw the header if it exists
        if header:
            logger.info(f"Drawing header: '{header}'")
            header_bbox = draw.textbbox((0, 0), header, font=header_font)
            header_height = header_bbox[3] - header_bbox[1]
            header_width = draw.textlength(header, font=header_font)
            header_x = (width - header_width) // 2
            header_y = margin
            draw.text((header_x, header_y), header, font=header_font, fill=FONT_CONFIG['DEFAULT_TEXT_COLOR'])
            start_y = header_y + header_height + margin
        else:
            start_y = margin * 2
        
        # Calculate and draw the footer if it exists
        if footer:
            logger.info(f"Drawing footer: '{footer}'")
            footer_bbox = draw.textbbox((0, 0), footer, font=header_font)
            footer_height = footer_bbox[3] - footer_bbox[1]
            footer_y = height - margin - footer_height
            draw.text(((width - draw.textlength(footer, font=header_font)) // 2, footer_y), 
                     footer, font=header_font, fill=FONT_CONFIG['DEFAULT_TEXT_COLOR'])
            end_y = footer_y - margin
        else:
            end_y = height - (margin * 2)
        
        # Process the main text if it is not empty
        if text.strip():
            logger.info(f"Processing main text (length: {len(text)})")
            
            # Get initial body font
            body_font = self._get_cached_font(st.session_state.body_font_path, font_size)
            
            # Calculate initial text height
            text_height = self._calculate_text_height(text, body_font, width, draw)
            available_height = end_y - start_y
            
            # Adjust font size to fit the available space
            while text_height > available_height and font_size > FONT_CONFIG['MIN_FONT_SIZE']:
                font_size -= 2
                body_font = self._get_cached_font(st.session_state.body_font_path, font_size)
                text_height = self._calculate_text_height(text, body_font, width, draw)
                logger.info(f"Adjusting font size to {font_size}, new text height: {text_height}")
            
            # Calculate the maximum number of characters per line
            avg_char_width = self.get_avg_char_width(draw, body_font)
            max_chars = int((width * 0.9) / avg_char_width)
            logger.info(f"Max chars per line: {max_chars}")
            
            # Split text into paragraphs and wrap each one
            paragraphs = text.split('\n\n')
            processed_paragraphs = []
            logger.info(f"Number of paragraphs: {len(paragraphs)}")
            
            for i, paragraph in enumerate(paragraphs):
                if not paragraph.strip():
                    processed_paragraphs.append("")
                    continue
                    
                wrapped_lines = wrap_paragraph(paragraph, max_chars)
                processed_paragraphs.extend(wrapped_lines)
                logger.info(f"Paragraph {i+1} wrapped into {len(wrapped_lines)} lines")
                
                if len(paragraphs) > 1:
                    processed_paragraphs.append("")
            
            if processed_paragraphs and not processed_paragraphs[-1]:
                processed_paragraphs.pop()
            
            # Calculate line spacing
            line_spacing = font_size * FONT_CONFIG['LINE_SPACING_FACTOR']
            
            # Calculate total height of text block
            text_block_height = len(processed_paragraphs) * line_spacing
            logger.info(f"Text block height: {text_block_height}")
            
            # Calculate starting y position to center the text block vertically
            y = start_y + (available_height - text_block_height) / 2
            logger.info(f"Starting y position: {y}")
            
            # Draw each line of text
            for i, line in enumerate(processed_paragraphs):
                if not line.strip():
                    y += line_spacing
                    continue
                
                logger.info(f"Drawing line {i+1}: '{line[:15]}{'...' if len(line) > 15 else ''}'")
                # Center each line horizontally
                x = (width - draw.textlength(line, font=body_font)) // 2
                self.draw_text_line(img, draw, line, x, y, font_size, FONT_CONFIG['DEFAULT_TEXT_COLOR'])
                y += line_spacing
        else:
            logger.info("No main text to process")
        
        # Return the image with preserved alpha channel
        return img.convert('RGBA')

    def _calculate_text_height(self, text: str, font: ImageFont.FreeTypeFont, width: int, 
                             draw: ImageDraw.Draw) -> float:
        """Calculate the total height needed for the text with the given font."""
        total_height = 0
        line_height = font.size * FONT_CONFIG['LINE_SPACING_FACTOR']
        
        # Calculate average character width for wrapping
        avg_char_width = self.get_avg_char_width(draw, font)
        max_chars = int((width * 0.9) / avg_char_width)
        
        paragraphs = text.split('\n\n')
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                total_height += line_height
                continue
                
            wrapped_lines = wrap_paragraph(paragraph, max_chars)
            total_height += len(wrapped_lines) * line_height
            
            # Add extra spacing between paragraphs
            if i < len(paragraphs) - 1:
                total_height += font.size * (FONT_CONFIG['LINE_SPACING_FACTOR'] - 1)
        
        return total_height
        
    def get_emoji_font(self, size: int) -> Optional[ImageFont.FreeTypeFont]:
        """Get cached emoji font with the specified size."""
        size = max(FONT_CONFIG['MIN_FONT_SIZE'], int(size))
        
        # Check cache first
        if size in self._emoji_font_cache:
            return self._emoji_font_cache[size]
        
        # If not in cache, try to load it
        emoji_font = load_emoji_font(size)
        if emoji_font is not None:
            self._emoji_font_cache[size] = emoji_font
            
        return emoji_font

# Public API
__all__ = [
    'create_text_image',  # Main image creation function
    'load_font',          # Font loading utility
    'validate_config',    # Configuration validation
    'FONT_CONFIG'         # Font configuration constants
]

def run_tests():
    """Run tests for text wrapping function."""
    # Test wrap_paragraph
    test_text = "This is a long paragraph that should be wrapped across multiple lines"
    wrapped = wrap_paragraph(test_text, max_chars=20)
    assert len(wrapped) > 1, "Text should be wrapped into multiple lines"
    assert all(len(line) <= 20 for line in wrapped), "All lines should be <= max_chars"
    print("✓ wrap_paragraph test passed")

    # Test wrap_paragraph with newlines
    test_text_newlines = "Line 1\nLine 2\nLine 3"
    wrapped = wrap_paragraph(test_text_newlines, max_chars=20)
    assert len(wrapped) == 1, "Newlines should be replaced with spaces"
    print("✓ wrap_paragraph newlines test passed")

    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    run_tests()
