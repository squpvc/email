"""
Configuration management for Project Phoenix.

This package handles all configuration settings, including user preferences,
application settings, and environment-specific configurations.
"""

import os
from pathlib import Path

# Base directory for the project
BASE_DIR = Path(__file__).parent.parent.parent

# Default configuration paths
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".phoenix")
LOG_DIR = os.path.join(CONFIG_DIR, "logs")
DATA_DIR = os.path.join(CONFIG_DIR, "data")

# Create necessary directories
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
