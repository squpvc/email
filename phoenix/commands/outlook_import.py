"""
Outlook Import Command.

This module provides a command for importing emails from Outlook PST/OST files.
"""

from typing import Optional, Dict, Any

from PyQt6.QtGui import QIcon

from phoenix.models.command import Command, CommandCategory
from ..ui.dialogs.outlook_import_dialog import show_outlook_import_dialog
from ..database import get_db_session


class OutlookImportCommand(Command):
    """Command to import emails from Outlook PST/OST files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = "Import from Outlook"
        self._description = "Import emails from Outlook PST/OST files"
        self._category = CommandCategory.IMPORT
        self._icon = QIcon(":/icons/mail-import.svg")
        self._shortcut = "Ctrl+Shift+O"
    
    def execute(self, app=None, params: Optional[Dict[str, Any]] = None) -> None:
        """Execute the command to show the Outlook import dialog."""
        if not app:
            return
            
        # Get the current user ID if available
        user_id = None
        if hasattr(app, 'current_user') and app.current_user:
            user_id = app.current_user.id
        
        # Show the import dialog
        show_outlook_import_dialog(
            parent=app.activeWindow(),
            db_session_factory=get_db_session,
            user_id=user_id
        )
    
    @property
    def is_available(self) -> bool:
        """Check if the command is available."""
        # Check if pypff is available
        try:
            import pypff  # noqa: F401
            return True
        except ImportError:
            return False
    
    @property
    def tooltip(self) -> str:
        """Get the tooltip for the command."""
        if not self.is_available:
            return "Outlook import requires the 'pypff-python' package to be installed."
        return self._description


# Register the command
def register() -> OutlookImportCommand:
    """Register the command with the command registry."""
    return OutlookImportCommand()
