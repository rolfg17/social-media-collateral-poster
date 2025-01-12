import re
import emoji
import logging

logger = logging.getLogger(__name__)

def clean_text_for_image(text):
    """Clean and format text for image rendering"""
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
    
    # Remove double quotes only (including smart quotes)
    text = text.replace('"', '').replace('"', '').replace('"', '')
    
    # Remove leading hyphens at the start of sections
    text = re.sub(r'(?m)^-\s*', '', text)
    
    # Normalize spacing in numbered lists (but preserve numbers)
    text = re.sub(r'(?m)^(\d+\.)\s+', r'\1 ', text)
    
    # Extract hashtags and put them on a new line
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
    
    # Add hashtags on a new line with proper spacing
    if hashtags:
        text = text.rstrip() + '\n\n' + ' '.join(sorted(set(hashtags)))
    
    # Clean up any leftover artifacts
    text = re.sub(r'\s+[.!?]', '.', text)  # Fix floating punctuation
    text = re.sub(r' {2,}', ' ', text)     # Remove multiple spaces but not newlines
    text = re.sub(r'[\n\s]*$', '', text)   # Remove trailing whitespace/newlines
    text = re.sub(r'^[\n\s]*', '', text)   # Remove leading whitespace/newlines
    
    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    
    # Remove empty parentheses that might be left after cleaning
    text = re.sub(r'\(\s*\)', '', text)
    
    # Ensure proper spacing between paragraphs
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def parse_markdown_content(content, config=None):
    """Parse sections from markdown content string"""
    sections = {}
    current_section = None
    current_content = []
    in_collaterals = False
    header_counts = {}
    
    collaterals_header = config.get('collaterals_header', '# Collaterals') if config else '# Collaterals'

    lines = content.split('\n')
    for line in lines:
        if line.strip() == collaterals_header:
            in_collaterals = True
            continue
        elif line.startswith("# ") and in_collaterals:
            break
        elif in_collaterals:
            if line.startswith("## "):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                base_section = line.lstrip("#").strip()
                if base_section in header_counts:
                    header_counts[base_section] += 1
                else:
                    header_counts[base_section] = 1
                current_section = f"{base_section} ({header_counts[base_section]})"
                current_content = []
            elif current_section is not None and not line.startswith("#"):
                current_content.append(line)

    if current_section and in_collaterals:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections
