import subprocess
import sys
import os

def main():
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, 'app.py')
    
    # Use the same Python interpreter that's running this script
    python_path = sys.executable
    streamlit_path = os.path.join(os.path.dirname(python_path), 'streamlit')
    
    # Run streamlit with the app
    subprocess.run([streamlit_path, 'run', app_path])

if __name__ == '__main__':
    main()
