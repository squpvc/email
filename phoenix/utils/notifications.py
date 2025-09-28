"""
Notification management for Project Phoenix.
"""
import logging
from typing import Optional, Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal

class NotificationManager(QObject):
    """Manages application notifications and alerts."""
    
    # Signal emitted when a notification should be shown
    notification_triggered = pyqtSignal(str, str)  # title, message
    
    def __init__(self, app):
        """Initialize the notification manager."""
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        self._enabled = True
        
        # Connect to application signals
        self.notification_triggered.connect(self._show_notification)
    
    @property
    def enabled(self) -> bool:
        """Get whether notifications are enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable notifications."""
        self._enabled = value
        self.logger.info(f"Notifications {'enabled' if value else 'disabled'}")
    
    def toggle_notifications(self) -> None:
        """Toggle notifications on/off."""
        self.enabled = not self.enabled
        
    def show_notification(self, title: str, message: str) -> None:
        """Show a notification.
        
        Args:
            title: The notification title
            message: The notification message
        """
        if self._enabled:
            self.notification_triggered.emit(title, message)
    
    def _show_notification(self, title: str, message: str) -> None:
        """Internal method to show a notification.
        
        This method can be overridden by platform-specific implementations.
        
        Args:
            title: The notification title
            message: The notification message
        """
        self.logger.info(f"Notification - {title}: {message}")
        # Default implementation just logs to console
        # Platform-specific implementations can be added here
        
        # For now, we'll show a simple message box
        from PyQt6.QtWidgets import QMessageBox
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
