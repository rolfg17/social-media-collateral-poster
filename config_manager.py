"""Configuration management for Social Media Collateral Poster.

This module handles loading and validating the application configuration.
"""

import json
from pathlib import Path
import logging
from ssl import DefaultVerifyPaths
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from exceptions import ConfigurationError
import os
import dotenv

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
        """Create FontConfig from dictionary data."""
        if not isinstance(data, dict):
            raise ConfigurationError("Font configuration must be a dictionary")
            
        required = ['paths', 'header_fonts', 'body_fonts']
        missing = [key for key in required if key not in data]
        if missing:
            raise ConfigurationError(f"Missing required font configuration keys: {missing}")
            
        # Ensure we have lists for fonts
        header_fonts = data.get('header_fonts', [])
        body_fonts = data.get('body_fonts', [])
        
        if not isinstance(header_fonts, list) or not isinstance(body_fonts, list):
            raise ConfigurationError("Header and body fonts must be lists")
        
        # Validate paths exist
        paths = data.get('paths', {})
        if not isinstance(paths, dict):
            raise ConfigurationError("Font paths must be a dictionary")
            
        # Filter out non-existent paths
        valid_paths = {}
        for font_name, path in paths.items():
            if path and os.path.exists(path):
                valid_paths[font_name] = path
            else:
                logger.warning(f"Font file not found: {path} for {font_name}")
        
        # If no valid fonts found, use system font
        if not valid_paths:
            fallback_font = "/System/Library/Fonts/Helvetica.ttc"
            if os.path.exists(fallback_font):
                valid_paths["System-Fallback"] = fallback_font
                if not header_fonts:
                    header_fonts = ["System-Fallback"]
                if not body_fonts:
                    body_fonts = ["System-Fallback"]
                logger.info(f"Using system fallback font: {fallback_font}")
            else:
                logger.error("System fallback font not found!")
        
        return cls(
            header_fonts=header_fonts,
            body_fonts=body_fonts,
            paths=valid_paths
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
    
    openai_api_key: str = ""
    """OpenAI API key for text generation."""
    
    obsidian_vault_path: str = ""
    """Path to the Obsidian vault where collaterals will be saved."""

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
            # Validate required string fields
            required_str_fields = ['header', 'footer', 'background_image_path']
            for field in required_str_fields:
                if field not in data:
                    raise ConfigurationError(
                        f"Missing required field: {field}",
                        f"The configuration must include a '{field}' value"
                    )
                value = data[field]
                if not isinstance(value, str):
                    raise ConfigurationError(
                        f"Invalid type for {field}",
                        f"Expected string, got {type(value)}"
                    )
                if not value.strip():
                    raise ConfigurationError(
                        f"Empty {field}",
                        f"The {field} field cannot be empty"
                    )
            
            # Get optional numeric fields with defaults
            width = data.get('width', cls.width)
            height = data.get('height', cls.height)
            font_size = data.get('font_size', cls.font_size)
            collaterals_header = data.get('collaterals_header', cls.collaterals_header)
            openai_api_key = data.get('openai_api_key', cls.openai_api_key)
            obsidian_vault_path = data.get('obsidian_vault_path', cls.obsidian_vault_path)
            
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
                
            # Validate and create font configuration
            if 'fonts' not in data:
                raise ConfigurationError(
                    "Missing fonts configuration",
                    "The configuration must include a 'fonts' section"
                )
            fonts = FontConfig.from_dict(data['fonts'])
            
            return cls(
                fonts=fonts,
                header=data['header'],
                footer=data['footer'],
                background_image_path=data['background_image_path'],
                width=width,
                height=height,
                font_size=font_size,
                collaterals_header=collaterals_header,
                openai_api_key=openai_api_key,
                obsidian_vault_path=obsidian_vault_path
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
            'collaterals_header': self.collaterals_header,
            'openai_api_key': self.openai_api_key,
            'obsidian_vault_path': self.obsidian_vault_path
        }
    
    def copy(self) -> Dict[str, Any]:
        """
        Create a copy of the configuration as a dictionary.

        Returns:
            Dict[str, Any]: A copy of the configuration data.
        """
        return self.to_dict()

class ConfigManager:
    """Configuration manager for the application."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the configuration manager."""
        self.config_path = config_path
        self._config = None
        
    def load_config(self) -> Config:
        """Load configuration from file."""
        if not os.path.exists(self.config_path):
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
            
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            # Validate and expand font paths
            if 'fonts' in config_data:
                font_paths = config_data['fonts'].get('paths', {})
                expanded_paths = {}
                for name, path in font_paths.items():
                    expanded_path = os.path.expanduser(path)
                    if os.path.exists(expanded_path):
                        expanded_paths[name] = expanded_path
                    else:
                        logger.warning(f"Font file not found: {expanded_path}")
                config_data['fonts']['paths'] = expanded_paths
            
            self._config = Config.from_dict(config_data)
            return self._config
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading config: {e}")

def get_env_api_key() -> str:
    """Get the API key from .env file only.
    
    Returns:
        str: The OpenAI API key from .env
        
    Raises:
        ConfigurationError: If .env file is missing or API key is not found
    """
    # Clear any existing OpenAI environment variables to ensure we only use .env
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    if 'OPENAI_KEY' in os.environ:
        del os.environ['OPENAI_KEY']
        
    # Load fresh from .env
    dotenv_path = Path(__file__).parent / '.env'
    if not dotenv_path.exists():
        raise ConfigurationError(
            "Missing .env file",
            f"Expected .env file at: {dotenv_path}"
        )
        
    dotenv.load_dotenv(dotenv_path)
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ConfigurationError(
            "Missing OpenAI API key",
            "OPENAI_API_KEY not found in .env file"
        )
    return api_key


def get_obsidian_vault_path() -> str:
    """Get the Obsidian vault path from the config file.
    
    Returns:
        str: The path to the Obsidian vault.
        
    Raises:
        ConfigurationError: If the config file is missing or the vault path is not found
    """
    #Load fresh from config file
    dotenv_path = Path(__file__).parent / '.env'
    if not dotenv_path.exists():
        raise ConfigurationError(
            "Missing .env file",
            f"Expected .env file at: {dotenv_path}"
        )
        
    dotenv.load_dotenv(dotenv_path)
    vault_path = os.getenv('OBSIDIAN_VAULT_PATH')
    if not vault_path:
        raise ConfigurationError(
            "Missing Obsidian vault path",
            "OBSIDIAN_VAULT_PATH not found in .env file"
        )
    return vault_path


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
        
        # Add OpenAI API key from .env file only
        data['openai_api_key'] = get_env_api_key()
        
        # Add Obsidian vault path from .env file only
        data['obsidian_vault_path'] = get_obsidian_vault_path()
            
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

def run_tests():
    """Run tests for config classes."""
    # Test FontConfig.from_dict
    font_data = {
        "header_fonts": ["Helvetica", "Arial"],
        "body_fonts": ["Helvetica", "Arial"],
        "paths": {
            "Helvetica": "/System/Library/Fonts/Helvetica.ttc",
            "Arial": "/System/Library/Fonts/Helvetica.ttc"  # Using Helvetica as fallback
        }
    }
    font_config = FontConfig.from_dict(font_data)
    assert font_config.header_fonts == ["Helvetica", "Arial"], "Header fonts should match"
    assert font_config.body_fonts == ["Helvetica", "Arial"], "Body fonts should match"
    assert font_config.paths == font_data["paths"], "Font paths should match"
    print("✓ FontConfig.from_dict test passed")

    # Test Config.from_dict with minimal valid configuration
    config_data = {
        "fonts": font_data,
        "header": "Test Header",
        "footer": "Test Footer",
        "background_image_path": "/System/Library/Desktop Pictures/Solid Colors/Solid Gray Light.png",
        "width": 800,
        "height": 600,
        "font_size": 32
    }
    config = Config.from_dict(config_data)
    assert config.header == "Test Header", "Header should match"
    assert config.width == 800, "Width should match"
    assert isinstance(config.fonts, FontConfig), "Fonts should be FontConfig instance"
    print("✓ Config.from_dict test passed")

    # Test Config dictionary access
    assert config["width"] == 800, "Dictionary access should work"
    assert config.get("height") == 600, "Get method should work"
    assert config.get("nonexistent", "default") == "default", "Get with default should work"
    assert "width" in config, "Contains check should work"
    print("✓ Config dictionary access test passed")

    # Test Config.to_dict
    config_dict = config.to_dict()
    assert config_dict["header"] == "Test Header", "to_dict should preserve header"
    assert config_dict["fonts"]["header_fonts"] == ["Helvetica", "Arial"], "to_dict should handle nested FontConfig"
    print("✓ Config.to_dict test passed")

    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    run_tests()
