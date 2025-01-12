import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PhotosExporter:
    def export(self, image_paths):
        """Export images to Photos app"""
        success = True
        results = []
        
        for path in image_paths:
            if not Path(path).exists():
                logger.error(f"Image file not found: {path}")
                results.append(f"❌ Failed: File not found - {path}")
                success = False
                continue
                
            apple_script = f'''
            tell application "Photos"
                activate
                delay 1
                try
                    import POSIX file "{path}"
                    return "Success"
                on error errMsg
                    return "Error: " & errMsg
                end try
            end tell
            '''
            
            try:
                result = subprocess.run(
                    ["osascript", "-e", apple_script], 
                    capture_output=True, 
                    text=True, 
                    check=False
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully imported {path}")
                    results.append(f"✅ Success: {path}")
                else:
                    logger.error(f"Error importing {path}: {result.stderr}")
                    results.append(f"❌ Failed: {result.stderr} - {path}")
                    success = False
            except Exception as e:
                logger.error(f"Exception while importing {path}: {str(e)}")
                results.append(f"❌ Failed: {str(e)} - {path}")
                success = False
        
        return success, results
