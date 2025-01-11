import json
import os
from pathlib import Path
import openai

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def extract_prompt_and_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split the content into sections
    sections = content.split('# ')
    
    # Find the Collaterals section
    main_content = ''
    prompt = ''
    
    for section in sections:
        if section.startswith('Collaterals'):
            # Extract prompt from Collaterals section
            prompt = section[len('Collaterals'):].strip()
        else:
            # Add other sections to main content
            if section.strip():
                main_content += '# ' + section if main_content else section
    
    if not prompt:
        raise ValueError("No '# Collaterals' section found in the file")
    
    return main_content.strip(), prompt

def generate_chatgpt_response(content, prompt, api_key):
    import httpx
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
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    
    # Ensure response starts with # Collaterals
    response_text = response.choices[0].message.content
    if not response_text.strip().startswith("# Collaterals"):
        response_text = "# Collaterals\n\n" + response_text
    
    return response_text

def save_response(response, input_file_path, vault_path):
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

def main():
    # Load configuration
    config = load_config()
    
    # Extract paths and API key
    vault_path = config['obsidian_vault_path']
    input_file_path = config['input_file_path']
    api_key = config['openai_api_key']
    
    # Process the input file
    content, prompt = extract_prompt_and_content(input_file_path)
    
    # Generate response from ChatGPT
    response = generate_chatgpt_response(content, prompt, api_key)
    
    # Save the response
    save_response(response, input_file_path, vault_path)
    
    print(f"Collaterals generated and saved successfully!")

if __name__ == "__main__":
    main()
