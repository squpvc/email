"""
Command models for the command palette.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Set, Any


class CommandCategory(str, Enum):
    """Categories for organizing commands in the palette."""
    GENERAL = "General"
    EMAIL = "Email"
    CALENDAR = "Calendar"
    TASKS = "Tasks"
    VIEW = "View"
    SETTINGS = "Settings"
    AI = "AI"
    IMPORT = "Import/Export"


@dataclass
class Command:
    """Represents a command in the command palette."""
    id: str
    name: str
    handler: Callable
    shortcut: str = ""
    icon: str = ""
    category: CommandCategory = CommandCategory.GENERAL
    description: str = ""
    keywords: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Initialize command with default values."""
        # Convert string category to CommandCategory enum if needed
        if isinstance(self.category, str):
            try:
                self.category = CommandCategory(self.category)
            except ValueError:
                # If the string doesn't match any enum value, default to GENERAL
                self.category = CommandCategory.GENERAL
        
        # Add name and category to keywords for search
        category_str = self.category.value if hasattr(self.category, 'value') else str(self.category)
        self.keywords.update([self.name.lower(), category_str.lower()])
        
        # Add description words to keywords
        if self.description:
            self.keywords.update(self.description.lower().split())
