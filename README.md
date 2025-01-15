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

3. (Optional) Set up Google Drive Export:
   1. Create a Google Cloud Project:
      - Go to [Google Cloud Console](https://console.cloud.google.com/)
      - Create a new project
      - Name it "Social Media Collateral Poster"

   2. Enable Google Drive API:
      - In the left menu, go to "APIs & Services" > "Library"
      - Search for "Google Drive API"
      - Click "Enable"

   3. Configure OAuth consent screen:
      - Go to "APIs & Services" > "OAuth consent screen"
      - Choose "External" user type
      - Fill in required fields:
        - App name: "Social Media Collateral Poster"
        - User support email: Your email
        - Developer contact email: Your email
      - Add your email as a test user

   4. Create OAuth credentials:
      - Go to "APIs & Services" > "Credentials"
      - Click "Create Credentials" > "OAuth client ID"
      - Choose "Desktop app"
      - Name: "Social Media Collateral Desktop Client"
      - Download the credentials.json file

   5. Create a .env file, or add to your existing .env file with the following content:
      ```
      GOOGLE_DRIVE_FOLDER_ID=your_folder_id
      GOOGLE_CREDENTIALS_PATH=path_to_credentials.json
      ```
      Note: Get the folder_id from your Google Drive folder URL: https://drive.google.com/drive/folders/FOLDER_ID

## Usage

1. Place your prompt at the end of your input Markdown file (last line).
2. Run the script:
   ```bash
   python generate_collaterals.py
   ```
3. The generated content will be saved in your vault with the same filename plus "-collaterals.md" suffix.
4. To export images to Google Drive:
   - Click "Connect Drive" in the sidebar (first time only)
   - Select the images you want to export
   - Click "Export to Drive"
   - View the results with direct links in the "Export Results" section

## File Structure
- The input file should contain your main content followed by the prompt on the last line
- The script will generate a new file with "-collaterals.md" suffix in your vault
