import json
import os
from pathlib import Path
import openai
import httpx
import tempfile
import logging
from dotenv import load_dotenv
from config_manager import get_env_api_key

logger = logging.getLogger(__name__)

def get_env_api_key():
    """Get the API key directly from .env to validate against"""
    # Clear any existing OpenAI environment variables to ensure we only use .env
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    if 'OPENAI_KEY' in os.environ:
        del os.environ['OPENAI_KEY']
        
    # Load fresh from .env
    dotenv_path = Path(__file__).parent / '.env'
    if not dotenv_path.exists():
        raise ValueError(f"Expected .env file at: {dotenv_path}")
        
    load_dotenv(dotenv_path)
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    return api_key

def extract_prompt_and_content(content):
    """
    Extracts the main content and prompt from markdown content
    
    Args:
        content (str): The markdown content as a string
    
    Returns:
        tuple: A tuple containing the main content and the prompt
    """
    # Split the content into sections
    sections = content.split('# ')
    
    # Find the Prompt section
    main_content = ''
    prompt = ''
    
    for section in sections:
        if section.startswith('Prompt'):
            # Extract prompt from Prompt section
            prompt = section[len('Prompt'):].strip()
        else:
            # Add other sections to main content
            if section.strip():
                main_content += '# ' + section if main_content else section
    
    if not prompt:
        raise ValueError("No '# Prompt' section found in the content")
    
    return main_content.strip(), prompt

def generate_chatgpt_response(content, prompt, api_key):
    """Generate collaterals using ChatGPT"""
    # Validate that the provided key matches the one in .env
    try:
        env_key = get_env_api_key()
        if api_key != env_key:
            raise ValueError("Provided API key does not match the key in .env file")
    except Exception as e:
        raise ValueError(str(e))
        
    logger.info(f"collateral_generator.py: Using OpenAI API key ending with: ...{api_key[-4:]}")
    client = openai.OpenAI(
        api_key=api_key,
        http_client=httpx.Client()
    )
    
    system_prompt = f"""Your task: {prompt}

IMPORTANT - You must format your response following these rules:
1. Start with "# Collaterals"
2. Use ONLY level 2 headers (##) for each social media section
3. Each section should start with "## 📱[Header from template]"
4. Put the content for each platform under its header
5. Do not use any other header levels

Example format:
# Collaterals

## 📸 Motivational Blurp
[Instagram content here]

## 💼 Contrarian Post
[LinkedIn content here]
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        # Ensure response starts with # Collaterals
        response_text = response.choices[0].message.content
        if not response_text.strip().startswith("# Collaterals"):
            response_text = "# Collaterals\n\n" + response_text
        
        return response_text
    except Exception as e:
        logger.error(f"Error generating collaterals: {str(e)}")
        raise

def process_and_save_collaterals(content, config):
    """
    Process markdown content and generate collaterals
    
    Args:
        content (str): The markdown content containing the newsletter and prompt
        config (dict): Configuration dictionary with API key
    
    Returns:
        str: Generated collaterals content
    """
    try:
        # Extract content and prompt
        main_content, prompt = extract_prompt_and_content(content)
        
        # Generate collaterals
        api_key = config['openai_api_key']
        response = generate_chatgpt_response(main_content, prompt, api_key)
        
        return response
            
    except Exception as e:
        logger.error(f"Error processing collaterals: {str(e)}")
        raise

def save_to_vault(response, input_file_path, vault_path):
    """Save the generated collaterals to the Obsidian vault"""
    # Get the original filename without extension
    input_filename = Path(input_file_path).stem
    
    # Find the next available counter
    counter = 0
    while True:
        # Create the new filename with counter if needed
        counter_suffix = f" {counter}" if counter > 0 else ""
        output_filename = f"{input_filename}-collaterals{counter_suffix}.md"
        output_path = Path(vault_path) / output_filename
        
        if not output_path.exists():
            break
        counter += 1
    
    # Add backlink to the original file
    backlink = f"Generated from: [[{input_filename}]]\n\n"
    
    # Validate and fix response format
    lines = response.split('\n')
    fixed_lines = []
    in_collaterals = False
    current_section = None
    
    for line in lines:
        # Handle Collaterals header
        if line.strip() == "# Collaterals":
            in_collaterals = True
            fixed_lines.append(line)
            continue
            
        if in_collaterals:
            # Fix section headers if needed
            if line.startswith('#'):
                if not line.startswith('## '):
                    # Convert any header to level 2
                    title = line.lstrip('#').strip()
                    if not title.startswith('Social Media:'):
                        title = f"Social Media: {title}"
                    if not any(emoji in title for emoji in ['📱', '📸', '💼', '🐦']):
                        title = f"📱 {title}"
                    line = f"## {title}"
                current_section = line
            fixed_lines.append(line)
    
    # Write the response with the backlink and fixed format
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(backlink + '\n'.join(fixed_lines))
        
    return output_path
