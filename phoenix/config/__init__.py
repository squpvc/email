"""
Configuration management for Project Phoenix.

This package handles all configuration settings, including user preferences,
application settings, and environment-specific configurations.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Base directory for the project
BASE_DIR = Path(__file__).parent.parent.parent

# Default configuration paths
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".phoenix")
LOG_DIR = os.path.join(CONFIG_DIR, "logs")
DATA_DIR = os.path.join(CONFIG_DIR, "data")
CACHE_DIR = os.path.join(CONFIG_DIR, "cache")
LOG_FILE = os.path.join(LOG_DIR, "phoenix.log")

# Application metadata
APP_NAME = "Project Phoenix"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Phoenix Team"
APP_DESCRIPTION = "A modern, AI-powered productivity suite"

# Create necessary directories
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "name": APP_NAME,
        "version": APP_VERSION,
        "author": APP_AUTHOR,
        "theme": "system",  # 'light', 'dark', or 'system'
        "font_size": 12,
        "language": "en_US",
        "check_for_updates": True
    },
    "window": {
        "width": 1200,
        "height": 800,
        "maximized": False,
        "position_x": None,
        "position_y": None
    },
    "email": {
        "default_provider": "imap",
        "check_interval": 300,  # seconds
        "notify_new_emails": True,
        "default_signature": ""
    },
    "ai": {
        "enabled": True,
        "model": "gpt-3.5-turbo",
        "max_tokens": 1000,
        "temperature": 0.7
    }
}
