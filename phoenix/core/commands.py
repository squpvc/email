"""
Core command definitions for Project Phoenix.

This module defines the base command classes and types used throughout the application.
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtGui import QKeySequence
    from PyQt6.QtCore import QObject


class CommandCategory(Enum):
    """Categories for organizing commands in the UI."""
    FILE = auto()
    EDIT = auto()
    VIEW = auto()
    TOOLS = auto()
    WINDOW = auto()
    HELP = auto()
    AI = auto()
    EMAIL = auto()
    CALENDAR = auto()
    TASKS = auto()
    SETTINGS = auto()


@dataclass
class Command:
    """A command that can be executed in the application.
    
    Args:
        id: Unique identifier for the command
        name: Display name
        description: Help text describing the command
        handler: Callable that executes the command
        category: Command category for organization
        shortcut: Keyboard shortcut (optional)
        icon: Icon name (optional)
        enabled: Whether the command is currently enabled
        visible: Whether the command should be shown in menus
    """
    id: str
    name: str
    description: str = ""
    handler: Optional[Callable[..., Any]] = None
    category: CommandCategory = CommandCategory.TOOLS
    shortcut: Optional['QKeySequence'] = None
    icon: Optional[str] = None
    enabled: bool = True
    visible: bool = True
    
    def execute(self, *args, **kwargs) -> Any:
        """Execute the command with the given arguments."""
        if self.handler is not None:
            return self.handler(*args, **kwargs)
        return None


class CommandRegistry:
    """Registry for managing application commands."""
    
    def __init__(self):
        self._commands: Dict[str, Command] = {}
    
    def register(self, command: Command) -> None:
        """Register a new command."""
        self._commands[command.id] = command
    
    def get(self, command_id: str) -> Optional[Command]:
        """Get a command by ID."""
        return self._commands.get(command_id)
    
    def get_all(self) -> List[Command]:
        """Get all registered commands."""
        return list(self._commands.values())
    
    def get_by_category(self, category: CommandCategory) -> List[Command]:
        """Get all commands in a category."""
        return [cmd for cmd in self._commands.values() if cmd.category == category]
    
    def unregister(self, command_id: str) -> None:
        """Unregister a command by ID."""
        if command_id in self._commands:
            del self._commands[command_id]


# Global command registry instance
command_registry = CommandRegistry()
