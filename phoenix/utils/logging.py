"""
Logging configuration for Project Phoenix.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log levels as strings for easier configuration
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

def setup_logging(
    log_file: Optional[str] = None,
    log_level: str = 'INFO',
    log_to_console: bool = True,
    log_to_file: bool = True
) -> None:
    """
    Configure logging for the application.
    
    Args:
        log_file: Path to the log file. If None, logs will be written to 
                 'phoenix.log' in the application's config directory.
        log_level: Logging level as a string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_to_console: Whether to log to console.
        log_to_file: Whether to log to a file.
    """
    # Ensure the log level is valid
    level = LOG_LEVELS.get(log_level.upper(), logging.INFO)
    
    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT
    )
    
    # Configure console logging
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Configure file logging
    if log_to_file:
        if log_file is None:
            # Default log file location
            log_dir = Path.home() / '.phoenix' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = str(log_dir / 'phoenix.log')
        
        # Ensure the log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Set up specific loggers
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    logger.info("Logging configured successfully")
    
    if log_to_file:
        logger.info(f"Log file: {log_file}")
    logger.info(f"Log level: {logging.getLevelName(level)}")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Name of the logger (usually __name__).
        
    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
