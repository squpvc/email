#!/usr/bin/env python3
"""
Main entry point for Project Phoenix.
"""
import argparse
import logging
import sys

from .application import run_application

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Project Phoenix - Unified Productivity Hub")
    
    # Add command line arguments
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode"
    )
    
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database connection URL (default: sqlite in user data directory)"
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('phoenix.log'),
            logging.StreamHandler()
        ]
    )
    
    # Run the application
    sys.exit(run_application())

if __name__ == "__main__":
    main()
