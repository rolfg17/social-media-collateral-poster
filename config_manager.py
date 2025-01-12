import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent / 'config.json'
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise
