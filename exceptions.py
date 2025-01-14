"""Custom exceptions for the Social Media Collateral Poster application.

Each exception class represents a specific type of error that can occur in the application.
This helps with:
1. Better error handling and debugging
2. More informative error messages
3. Proper error categorization
"""

class SocialMediaCollateralError(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.full_message)
    
    @property
    def full_message(self) -> str:
        """Returns the full error message including details if available."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message

class ConfigurationError(SocialMediaCollateralError):
    """Raised when there is an error in the configuration.
    
    Examples:
        - Missing required configuration fields
        - Invalid configuration values
        - File paths that don't exist
    """
    pass

class FontError(SocialMediaCollateralError):
    """Raised when there are issues with font loading or handling.
    
    Examples:
        - Font file not found
        - Invalid font size
        - Failed to load font
    """
    pass

class ImageError(SocialMediaCollateralError):
    """Raised when there are issues with image processing.
    
    Examples:
        - Failed to create image
        - Image size issues
        - Drawing errors
    """
    pass

class TextError(SocialMediaCollateralError):
    """Raised when there are issues with text processing.
    
    Examples:
        - Text cleaning errors
        - Markdown parsing issues
        - Text too long for image
    """
    pass

class FileOperationError(SocialMediaCollateralError):
    """Raised when there are issues with file operations.
    
    Examples:
        - Failed to read/write files
        - Permission issues
        - File not found
    """
    pass

class ExportError(SocialMediaCollateralError):
    """Raised when there are issues exporting images.
    
    Examples:
        - Failed to save to Photos app
        - Export path issues
        - Format conversion errors
    """
    pass
