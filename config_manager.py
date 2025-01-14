"""Configuration management for Social Media Collateral Poster.

This module handles loading and validating the application configuration.
"""

import json
from pathlib import Path
import logging
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from exceptions import ConfigurationError

logger = logging.getLogger(__name__)

@dataclass
class FontConfig:
    """Font configuration settings."""
    
    header_fonts: List[str]
    """Header font names, ordered by preference."""
    
    body_fonts: List[str]
    """Body font names, ordered by preference."""
    
    paths: Dict[str, str]
    """Font paths, keyed by font name."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FontConfig':
        """
        Create a FontConfig instance from a dictionary.
        
        Args:
            data (Dict[str, Any]): A dictionary containing font configuration.
        
        Returns:
            FontConfig: An instance of FontConfig.
        
        Raises:
            ConfigurationError: If font files do not exist or required fields are missing.
        """
        try:
            # Extract paths, header fonts, and body fonts from the dictionary
            paths = data.get('paths', {})
            header_fonts = data.get('header_fonts', [])
            body_fonts = data.get('body_fonts', [])

            # Validate that the font paths exist
            for name, path in paths.items():
                if not Path(path).is_file():
                    raise ConfigurationError(
                        f"Font file not found: {name}",
                        f"Path does not exist: {path}"
                    )

            return cls(
                header_fonts=header_fonts,
                body_fonts=body_fonts,
                paths=paths
            )
        except KeyError as e:
            raise ConfigurationError(
                "Missing required font configuration",
                f"Missing field: {str(e)}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the FontConfig instance to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the FontConfig instance.
        """
        return asdict(self)

@dataclass
class Config:
    """Application configuration."""
    
    fonts: FontConfig
    """Font configuration settings, including paths and font preferences."""
    
    header: str
    """Header text for the application."""
    
    footer: str
    """Footer text for the application."""
    
    background_image_path: str
    """Path to the background image used in the application."""
    
    width: int = 700
    """Default width for image generation."""
    
    height: int = 700
    """Default height for image generation."""
    
    font_size: int = 40
    """Default font size for text."""
    
    collaterals_header: str = "# Collaterals"
    """Default header text for collaterals."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """
        Create a Config instance from a dictionary.

        Args:
            data (Dict[str, Any]): A dictionary containing configuration data.

        Returns:
            Config: An instance of Config.

        Raises:
            ConfigurationError: If required fields are missing or invalid.
        """
        try:
            # Parse font configuration
            fonts = FontConfig.from_dict(data.get('fonts', {}))
            
            # Retrieve required configuration fields
            header = data.get('header')
            footer = data.get('footer')
            background_image_path = data.get('background_image_path')
            
            if not all([header, footer, background_image_path]):
                missing = [k for k, v in {'header': header, 'footer': footer, 
                          'background_image_path': background_image_path}.items() if not v]
                raise ConfigurationError(
                    "Missing required configuration fields",
                    f"Missing fields: {', '.join(missing)}"
                )
            
            # Retrieve optional fields with defaults
            width = data.get('width', cls.width)
            height = data.get('height', cls.height)
            font_size = data.get('font_size', cls.font_size)
            collaterals_header = data.get('collaterals_header', cls.collaterals_header)

            # Validate dimensions and font size
            if width <= 0 or height <= 0:
                raise ConfigurationError(
                    "Invalid dimensions",
                    f"Width and height must be positive (got {width}x{height})"
                )
            
            if font_size <= 0:
                raise ConfigurationError(
                    "Invalid font size",
                    f"Font size must be positive (got {font_size})"
                )

            return cls(
                fonts=fonts,
                header=header,
                footer=footer,
                background_image_path=background_image_path,
                width=width,
                height=height,
                font_size=font_size,
                collaterals_header=collaterals_header
            )
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                "Failed to create configuration",
                str(e)
            )

    def __getitem__(self, key: str) -> Any:
        """
        Allow dictionary-style access to configuration values.

        Args:
            key (str): The configuration field name.

        Returns:
            Any: The value of the specified configuration field.

        Raises:
            KeyError: If the field is not present in the configuration.
        """
        if hasattr(self, key):
            value = getattr(self, key)
            if isinstance(value, FontConfig):
                return value.to_dict()
            return value
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        """
        Support 'in' operator for checking configuration keys.

        Args:
            key (str): The configuration field name.

        Returns:
            bool: True if the key exists in the configuration, False otherwise.
        """
        return hasattr(self, key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Dictionary-style get method with a default value.

        Args:
            key (str): The configuration field name.
            default (Any, optional): The default value to return if key is not found.

        Returns:
            Any: The value of the specified configuration field, or the default.
        """
        try:
            return self[key]
        except KeyError:
            return default
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Config instance to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the Config instance.
        """
        return {
            'fonts': self.fonts.to_dict(),
            'header': self.header,
            'footer': self.footer,
            'background_image_path': self.background_image_path,
            'width': self.width,
            'height': self.height,
            'font_size': self.font_size,
            'collaterals_header': self.collaterals_header
        }
    
    def copy(self) -> Dict[str, Any]:
        """
        Create a copy of the configuration as a dictionary.

        Returns:
            Dict[str, Any]: A copy of the configuration data.
        """
        return self.to_dict()

def load_config() -> Config:
    """Load configuration from config.json file.
    
    Returns:
        Config: Validated configuration object
        
    Raises:
        ConfigurationError: If config file is missing, invalid, or contains errors
    """
    config_path = Path(__file__).parent / 'config.json'
    
    try:
        if not config_path.exists():
            raise ConfigurationError(
                "Configuration file not found",
                f"Expected config file at: {config_path}"
            )
            
        with open(config_path, 'r') as f:
            data = json.load(f)
            
        return Config.from_dict(data)
        
    except json.JSONDecodeError as e:
        raise ConfigurationError(
            "Invalid JSON in config file",
            str(e)
        )
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(
            "Failed to load configuration",
            str(e)
        )
