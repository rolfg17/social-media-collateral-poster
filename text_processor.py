"""Text processing utilities for Social Media Collateral Poster."""

import re
import logging
from typing import Tuple, List, Dict, Any
from exceptions import TextError

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class TextProcessor:
    """Handles text processing and cleaning operations."""
    
    def __init__(self):
        """Initialize the text processor."""
        pass
    
    def clean_urls(self, text: str) -> str:
        """Remove URLs and URL-related artifacts from text."""
        try:
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
            
            return text
        except Exception as e:
            raise TextError("Failed to clean URLs", str(e))

    def clean_markdown(self, text: str) -> str:
        """Remove markdown formatting while preserving content."""
        try:
            # Remove markdown highlights (**, _, *, __, ~~)
            text = text.replace('~~', '')
            text = text.replace('**', '')
            text = text.replace('_', '')
            text = text.replace('*', '')
            text = text.replace('__', '')
            text = text.replace('**', '')

            # Replace double hyphens
            text = text.replace('--', '')
            
            # Remove double quotes only (including smart quotes)
            text = text.replace('"', '').replace('"', '').replace('"', '')
            
            # Remove leading hyphens at the start of sections
            text = re.sub(r'(?m)^-\s*', '', text)
            
            # Normalize spacing in numbered lists (but preserve numbers)
            text = re.sub(r'(?m)^(\d+\.)\s+', r'\1 ', text)
            
            return text
        except Exception as e:
            raise TextError("Failed to clean markdown", str(e))

    def process_hashtags(self, text: str) -> Tuple[str, List[str]]:
        """Extract hashtags and return cleaned text and hashtag list."""
        try:
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
            
            return text, hashtags
        except Exception as e:
            raise TextError("Failed to process hashtags", str(e))

    def normalize_spacing(self, text: str) -> str:
        """Clean up spacing and formatting in text."""
        try:
            # Remove extra whitespace while preserving paragraph breaks
            paragraphs = text.split('\n\n')
            cleaned_paragraphs = []
            
            for para in paragraphs:
                # Normalize internal whitespace
                lines = [line.strip() for line in para.split('\n')]
                cleaned_lines = [' '.join(line.split()) for line in lines if line]
                cleaned_para = ' '.join(cleaned_lines)
                if cleaned_para:
                    cleaned_paragraphs.append(cleaned_para)
            
            return '\n\n'.join(cleaned_paragraphs)
        except Exception as e:
            raise TextError("Failed to normalize spacing", str(e))

    def clean_text_for_image(self, text: str) -> str:
        """Clean and format text for image rendering."""
        try:
            if not text or not text.strip():
                return ""
                
            # Remove URLs first
            text = self.clean_urls(text)
            if not text.strip():
                return ""
                
            # Clean markdown formatting
            text = self.clean_markdown(text)
            if not text.strip():
                return ""
                
            # Normalize spacing (don't process hashtags)
            text = self.normalize_spacing(text)
            if not text.strip():
                return ""
                
            logger.debug(f"Cleaned text: {text[:100]}...")
            return text
            
        except Exception as e:
            logger.error(f"Failed to clean text: {str(e)}", exc_info=True)
            raise TextError("Failed to clean text for image", str(e))

    def parse_markdown_content(self, content: str, config: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Parse sections from markdown content string.

        This function takes a markdown content string and returns a dictionary
        of sections, where each section is a header followed by its content.

        Args:
            content: The markdown content string
            config: A dictionary of configuration options

        Returns:
            A dictionary of sections
        """
        sections = {}
        current_section = None
        current_content = []
        in_collaterals = False
        header_counts = {}

        # Define the header that marks the start of the Collaterals section
        collaterals_header = config.get('collaterals_header', '# Collaterals') if config else '# Collaterals'

        # Split the content into lines and clean up empty lines
        lines = [line.rstrip() for line in content.split('\n')]

        # Iterate over the lines
        for line in lines:
            stripped_line = line.strip()
            if stripped_line == collaterals_header:
                # We've reached the Collaterals section
                in_collaterals = True
                continue
            elif stripped_line.startswith("# Feel free") or stripped_line.startswith("# Note"):
                # Skip common ending notes
                continue
            elif in_collaterals and stripped_line:  # Only process non-empty lines
                # Check for any level of header (# through ###)
                if re.match(r'^#{1,3}\s', stripped_line):
                    # Save the current section before starting a new one
                    if current_section and current_content:
                        content_text = '\n'.join(current_content).strip()
                        if content_text:  # Only save if there's actual content
                            sections[current_section] = content_text
                        current_content = []
                    
                    # Get the base section name without number and hashes
                    base_section = stripped_line.lstrip("#").strip()
                    
                    # Update counter for this section title
                    if base_section in header_counts:
                        header_counts[base_section] += 1
                        current_section = f"{base_section} ({header_counts[base_section]})"
                    else:
                        header_counts[base_section] = 1
                        current_section = base_section
                    
                    logger.debug(f"Processing section: {current_section}")
                else:
                    if current_section and stripped_line:  # Only add non-empty lines
                        current_content.append(stripped_line)

        # Add the last section if it has content
        if current_section and current_content:
            content_text = '\n'.join(current_content).strip()
            if content_text:  # Only save if there's actual content
                sections[current_section] = content_text

        # Log the found sections
        if sections:
            logger.debug(f"Found sections: {list(sections.keys())}")
        else:
            logger.error("No valid sections found in the markdown file")

        return sections


def run_tests():
    """Run tests for text processing functions.
    
    Note: Tests are run sequentially and will stop at the first failure.
    Only success messages for tests that passed before the failure will be shown.
    For more detailed test reporting, consider using unittest or pytest."""
    processor = TextProcessor()
    # Test clean_urls
    test_url_text = "Check out [my link](https://example.com) and https://another.com?utm_source=test"
    assert "Check out my link and " == processor.clean_urls(test_url_text)
    print("✓ clean_urls test passed")

    # Test clean_markdown
    test_md_text = "**Bold** and _italic_ text with ~~strikethrough~~"
    assert "Bold and italic text with strikethrough" == processor.clean_markdown(test_md_text)
    print("✓ clean_markdown test passed")

    # Test process_hashtags
    test_hashtag_text = "Hello #world! This is a #test-post with #multiple #hashtags"
    cleaned_text, hashtags = processor.process_hashtags(test_hashtag_text)
    assert cleaned_text.strip() == "Hello ! This is a with"
    assert sorted(hashtags) == ["#hashtags", "#multiple", "#test-post", "#world"]
    print("✓ process_hashtags test passed")

    # Test normalize_spacing
    test_spacing_text = "Too  many    spaces  and\n\n\nextra\n\n\nlines"
    assert "Too many spaces and\n\nextra\n\nlines" == processor.normalize_spacing(test_spacing_text)
    print("✓ normalize_spacing test passed")

    # Test clean_text_for_image
    test_full_text = "**Hello** [world](https://example.com)!\n#test #python"
    result = processor.clean_text_for_image(test_full_text)
    expected = "Hello world!\n\n#python #test"
    assert result == expected
    print("✓ clean_text_for_image test passed")

    print("\nAll tests passed successfully!")


if __name__ == "__main__":
    run_tests()
