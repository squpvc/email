"""
Base application interface for Project Phoenix.

This module defines the base interface for the Phoenix application to avoid circular imports.
"""
from typing import Any, Dict, Optional, Type, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QFont


class PhoenixApplicationBase(QObject):
    """Base interface for the Phoenix application.
    
    This class defines the interface that the main application class must implement.
    It's used to break circular imports between the application and UI components.
    """
    # Signals
    theme_changed = pyqtSignal(str)
    font_changed = pyqtSignal(QFont)
    shutdown_signal = pyqtSignal()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get an application setting."""
        raise NotImplementedError()
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set an application setting."""
        raise NotImplementedError()
    
    def get_theme(self) -> str:
        """Get the current theme name."""
        raise NotImplementedError()
    
    def set_theme(self, theme_name: str) -> None:
        """Set the current theme."""
        raise NotImplementedError()
    
    def get_font(self) -> str:
        """Get the current font."""
        raise NotImplementedError()
    
    def set_font(self, font_family: str, size: int) -> None:
        """Set the current font."""
        raise NotImplementedError()
    
    def show_notification(self, title: str, message: str, level: str = "info") -> None:
        """Show a notification to the user."""
        raise NotImplementedError()
    
    def execute_command(self, command_name: str, **kwargs) -> Any:
        """Execute a command by name."""
        raise NotImplementedError()
    
    def register_command(self, command: 'Command') -> None:
        """Register a command with the application."""
        raise NotImplementedError()
    
    def unregister_command(self, command_name: str) -> None:
        """Unregister a command from the application."""
        raise NotImplementedError()
    
    def get_commands(self) -> Dict[str, 'Command']:
        """Get all registered commands."""
        raise NotImplementedError()
    
    def get_command(self, command_name: str) -> Optional['Command']:
        """Get a command by name."""
        raise NotImplementedError()
    
    def show_command_palette(self) -> None:
        """Show the command palette."""
        raise NotImplementedError()
    
    def show_settings_dialog(self) -> None:
        """Show the settings dialog."""
        raise NotImplementedError()
