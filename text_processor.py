"""Text processing utilities for Social Media Collateral Poster."""

import re
import logging
from typing import Tuple, List, Dict, Any
from exceptions import TextError

# Set up logging once at module level
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set logger level to DEBUG
logger.propagate = False

# Remove any existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add a handler to show DEBUG messages
debug_handler = logging.StreamHandler()
debug_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s: %(message)s')
debug_handler.setFormatter(formatter)
logger.addHandler(debug_handler)

def clean_urls(text: str) -> str:
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

def clean_markdown(text: str) -> str:
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

def process_hashtags(text: str) -> Tuple[str, List[str]]:
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
        
        return text, sorted(set(hashtags))
    except Exception as e:
        raise TextError("Failed to process hashtags", str(e))

def normalize_spacing(text: str) -> str:
    """Clean up spacing and formatting in text."""
    try:
        # Fix floating punctuation
        text = re.sub(r'\s+[.!?]', '.', text)
        
        # Remove multiple spaces but not newlines
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove trailing/leading whitespace/newlines
        text = re.sub(r'[\n\s]*$', '', text)
        text = re.sub(r'^[\n\s]*', '', text)
        
        # Fix spacing around punctuation
        text = re.sub(r'\s+([.,!?])', r'\1', text)
        
        # Remove empty parentheses
        text = re.sub(r'\(\s*\)', '', text)
        
        # Ensure proper spacing between paragraphs
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    except Exception as e:
        raise TextError("Failed to normalize spacing", str(e))

def clean_text_for_image(text: str) -> str:
    """Clean and format text for image rendering"""
    try:
        # Clean URLs and markdown
        text = clean_urls(text)
        text = clean_markdown(text)
        
        # Process hashtags
        main_text, hashtags = process_hashtags(text)
        
        # Add hashtags on a new line with proper spacing
        if hashtags:
            main_text = main_text.rstrip() + '\n\n' + ' '.join(hashtags)
        
        # Final cleanup
        text = normalize_spacing(main_text)
        
        return text
    except TextError:
        raise
    except Exception as e:
        raise TextError("Failed to clean text for image", str(e))

def parse_markdown_content(content: str, config: Dict[str, Any] = None) -> Dict[str, str]:
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

    # Split the content into lines
    lines = content.split('\n')

    # Iterate over the lines
    for line in lines:
        if line.strip() == collaterals_header:
            # We've reached the Collaterals section
            in_collaterals = True
            continue
        elif line.startswith("# Feel free") or line.startswith("# Note"):
            # Skip common ending notes
            continue
        elif in_collaterals:
            # Check for any level of header (# through ###)
            if re.match(r'^#{1,3}\s', line):
                # We've reached a new section
                if current_section:
                    # Add the current section to the dictionary
                    sections[current_section] = '\n'.join(current_content).strip()
                    current_content = []
                
                # Get the base section name without number and hashes
                base_section = line.lstrip("#").strip()
                
                # Update counter for this section title
                if base_section in header_counts:
                    header_counts[base_section] += 1
                    current_section = f"{base_section} ({header_counts[base_section]})"
                else:
                    header_counts[base_section] = 1
                    current_section = base_section
                
                logger.debug(f"Processing section: {current_section}")
            else:
                if current_section:
                    current_content.append(line)

    # Add the last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections

def run_tests():
    """Run tests for text processing functions.
    
    Note: Tests are run sequentially and will stop at the first failure.
    Only success messages for tests that passed before the failure will be shown.
    For more detailed test reporting, consider using unittest or pytest."""
    # Test clean_urls
    test_url_text = "Check out [my link](https://example.com) and https://another.com?utm_source=test"
    assert "Check out my link and " == clean_urls(test_url_text)
    print("✓ clean_urls test passed")

    # Test clean_markdown
    test_md_text = "**Bold** and _italic_ text with ~~strikethrough~~"
    assert "Bold and italic text with strikethrough" == clean_markdown(test_md_text)
    print("✓ clean_markdown test passed")

    # Test process_hashtags
    test_hashtag_text = "Hello #world! This is a #test-post with #multiple #hashtags"
    cleaned_text, hashtags = process_hashtags(test_hashtag_text)
    assert cleaned_text.strip() == "Hello ! This is a with"
    assert sorted(hashtags) == ["#hashtags", "#multiple", "#test-post", "#world"]
    print("✓ process_hashtags test passed")

    # Test normalize_spacing
    test_spacing_text = "Too  many    spaces  and\n\n\nextra\n\n\nlines"
    assert "Too many spaces and\n\nextra\n\nlines" == normalize_spacing(test_spacing_text)
    print("✓ normalize_spacing test passed")

    # Test clean_text_for_image
    test_full_text = "**Hello** [world](https://example.com)!\n#test #python"
    result = clean_text_for_image(test_full_text)
    expected = "Hello world!\n\n#python #test"
    assert result == expected
    print("✓ clean_text_for_image test passed")

    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    run_tests()
