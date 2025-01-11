# Obsidian ChatGPT Collateral Generator

This script processes Markdown files from your Obsidian vault using ChatGPT and generates collateral content based on the file's content and a prompt.

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure the `config.json` file:
   - Set your Obsidian vault path
   - Set the input file path
   - Add your OpenAI API key

## Usage

1. Place your prompt at the end of your input Markdown file (last line).
2. Run the script:
   ```bash
   python generate_collaterals.py
   ```
3. The generated content will be saved in your vault with the same filename plus "-collaterals.md" suffix.

## File Structure
- The input file should contain your main content followed by the prompt on the last line
- The script will generate a new file with "-collaterals.md" suffix in your vault
