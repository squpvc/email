"""
AI and machine learning integration for Project Phoenix.
"""

# AI Module

# This package provides AI-powered features such as natural language processing,
# semantic search, and intelligent email handling.

from .services import (
    ai_service,
    AI_AVAILABLE,
    EmailSummary,
    EmailCategory,
    EmailPriority,
    EmailClassification,
    EmailSearchResult
)

from .command_handler import (
    AICommand,
    AICommandHandler
)

# Create a singleton instance of the command handler
ai_command_handler = AICommandHandler()

def get_ai_commands():
    """Get all registered AI commands."""
    if not AI_AVAILABLE:
        return []
    return ai_command_handler.get_commands()

__all__ = [
    'ai_service',
    'AI_AVAILABLE',
    'EmailSummary',
    'EmailCategory',
    'EmailPriority',
    'EmailClassification',
    'EmailSearchResult',
    'AICommand',
    'AICommandHandler',
    'ai_command_handler',
    'get_ai_commands'
]
