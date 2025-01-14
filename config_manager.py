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
    body_fonts: List[str]
    paths: Dict[str, str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FontConfig':
        """Create FontConfig from dictionary."""
        try:
            paths = data.get('paths', {})
            header_fonts = data.get('header_fonts', [])
            body_fonts = data.get('body_fonts', [])

            # Validate font paths exist
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
        """Convert to dictionary."""
        return asdict(self)

@dataclass
class Config:
    """Application configuration."""
    fonts: FontConfig
    header: str
    footer: str
    background_image_path: str
    width: int = 700
    height: int = 700
    font_size: int = 40
    collaterals_header: str = "# Collaterals"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary."""
        try:
            fonts = FontConfig.from_dict(data.get('fonts', {}))
            
            # Get required fields
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
            
            # Get optional settings with defaults
            width = data.get('width', cls.width)
            height = data.get('height', cls.height)
            font_size = data.get('font_size', cls.font_size)
            collaterals_header = data.get('collaterals_header', cls.collaterals_header)

            # Validate numeric values
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
        """Allow dictionary-style access to configuration."""
        if hasattr(self, key):
            value = getattr(self, key)
            if isinstance(value, FontConfig):
                return value.to_dict()
            return value
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for configuration keys."""
        return hasattr(self, key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-style get method with default value."""
        try:
            return self[key]
        except KeyError:
            return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
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
        """Create a copy of the configuration as a dictionary."""
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
