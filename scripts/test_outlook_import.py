"""
Test script for Outlook import functionality.

This script demonstrates how to use the Outlook import feature programmatically.
It can be used for testing and as a reference for integration.
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('outlook_import_test.log')
    ]
)
logger = logging.getLogger(__name__)

def test_outlook_import():
    """Test the Outlook import functionality."""
    try:
        # Import required modules
        from phoenix.ui.dialogs.outlook_import_dialog import show_outlook_import_dialog
        from phoenix.database import get_db_session, init_db
        from phoenix.models.user import User
        
        # Initialize database
        init_db()
        
        # Create a test user if needed
        with get_db_session() as session:
            user = session.query(User).filter_by(email="test@example.com").first()
            if not user:
                user = User(
                    email="test@example.com",
                    name="Test User"
                )
                session.add(user)
                session.commit()
        
        # Create application instance
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Set up application mock
        class MockApp:
            def activeWindow(self):
                return None
            
            @property
            def current_user(self):
                return user
        
        # Show the import dialog
        logger.info("Showing Outlook import dialog...")
        show_outlook_import_dialog(
            parent=None,
            db_session_factory=get_db_session,
            user_id=user.id
        )
        
        # Set up auto-close timer
        QTimer.singleShot(3000, app.quit)  # Close after 3 seconds for testing
        
        # Run the application
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Error testing Outlook import: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(test_outlook_import())
