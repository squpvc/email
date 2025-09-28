"""
AI Command Handler.

This module handles the registration and execution of AI-powered commands
in the application's command palette.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal

from ..core.commands import Command, CommandCategory
from .services import ai_service, AI_AVAILABLE

if AI_AVAILABLE:
    from .services import EmailSummary, EmailClassification  # noqa: F401

class AICommand(Command):
    """Extended Command class for AI-powered commands."""

    def __init__(self, id: str, name: str, description: str, category: Any, 
                 handler: callable, requires_selection: bool = False, 
                 requires_thread: bool = False, icon: Optional[str] = None, **kwargs):
        """Initialize an AI command.
        
        Args:
            id: Unique identifier for the command
            name: Display name of the command
            description: Description of what the command does
            category: Category the command belongs to
            handler: Function to call when the command is executed
            requires_selection: Whether the command requires selected text
            requires_thread: Whether the command requires an email thread
            icon: Optional icon for the command
            **kwargs: Additional keyword arguments to pass to the parent class
        """
        super().__init__(id, name, description, category, icon=icon, **kwargs)
        self.handler = handler
        self.requires_selection = requires_selection
        self.requires_thread = requires_thread

class AICommandHandler(QObject):
    """Handles AI-powered commands and their execution."""

    # Signals
    command_executed = pyqtSignal(str, dict)  # command_name, result
    error_occurred = pyqtSignal(str, str)  # command_name, error_message

    def __init__(self, parent=None):
        """Initialize the AI command handler.

        Args:
            parent: The parent QObject.
        """
        super().__init__(parent)
        self._commands: Dict[str, AICommand] = {}
        self._selected_text: str = ""
        self._current_thread: Optional[Dict[str, Any]] = None
        
        # Register AI commands
        self._register_commands()
    
    def _register_commands(self) -> None:
        """Register all AI-powered commands."""
        if not AI_AVAILABLE:
            return
            
        commands = [
            AICommand(
                id="ai.summarize",
                name="Summarize Email",
                description="Generate a summary of the selected email or thread",
                category=CommandCategory.AI,
                icon="summarize",
                shortcut="Ctrl+Alt+S",
                requires_selection=True,
                handler=self._handle_summarize
            ),
            AICommand(
                id="ai.reply",
                name="Suggest Reply",
                description="Generate a suggested reply to the current email",
                category=CommandCategory.AI,
                icon="reply",
                shortcut="Ctrl+Alt+R",
                requires_thread=True,
                handler=self._handle_suggest_reply
            ),
            AICommand(
                id="ai.extract_actions",
                name="Extract Action Items",
                description="Extract action items from the selected email or thread",
                category=CommandCategory.AI,
                icon="checklist",
                shortcut="Ctrl+Alt+A",
                requires_selection=True,
                handler=self._handle_extract_actions
            ),
            AICommand(
                id="ai.search",
                name="AI Search",
                description="Search emails using natural language",
                category=CommandCategory.AI,
                icon="search",
                shortcut="Ctrl+K",
                handler=self._handle_search
            )
        ]
        
        for cmd in commands:
            self.register_command(cmd)
    
    def register_command(self, command: AICommand) -> None:
        """Register a new AI command."""
        self._commands[command.id] = command
    
    def get_commands(self) -> List[AICommand]:
        """Get all registered AI commands."""
        return list(self._commands.values())
    
    def set_selected_text(self, text: str) -> None:
        """Set the currently selected text in the UI."""
        self._selected_text = text.strip()
    
    def set_current_thread(self, thread: Dict[str, Any]) -> None:
        """Set the current email thread context."""
        self._current_thread = thread
    
    def execute_command(self, command_id: str) -> None:
        """Execute an AI command by ID."""
        if not AI_AVAILABLE:
            self.error_occurred.emit(command_id, "AI features are not available")
            return
            
        command = self._commands.get(command_id)
        if not command:
            self.error_occurred.emit(command_id, f"Unknown command: {command_id}")
            return
            
        try:
            # Check preconditions
            if command.requires_selection and not self._selected_text:
                self.error_occurred.emit(command_id, "No text selected")
                return
                
            if command.requires_thread and not self._current_thread:
                self.error_occurred.emit(command_id, "No email thread selected")
                return
            
            # Execute the command
            result = command.handler()
            self.command_executed.emit(command_id, result)
            
        except Exception as e:
            self.error_occurred.emit(command_id, str(e))
    
    # Command Handlers
    def _handle_summarize(self) -> Dict[str, Any]:
        """Handle the summarize command."""
        if not self._current_thread:
            raise ValueError("No email thread selected")
            
        summary = ai_service.summarize_email(
            subject=self._current_thread.get("subject", ""),
            body=self._current_thread.get("body", "")
        )
        
        return {
            "type": "summary",
            "summary": summary.summary,
            "key_points": summary.key_points,
            "action_items": summary.action_items
        }
    
    def _handle_suggest_reply(self) -> Dict[str, Any]:
        """Handle the suggest reply command."""
        if not self._current_thread:
            raise ValueError("No email thread selected")
            
        reply = ai_service.suggest_reply(
            email_subject=self._current_thread.get("subject", ""),
            email_body=self._current_thread.get("body", "")
        )
        
        return {
            "type": "reply_suggestion",
            "suggestion": reply
        }
    
    def _handle_extract_actions(self) -> Dict[str, Any]:
        """Handle the extract action items command."""
        if not self._current_thread:
            raise ValueError("No email thread selected")
            
        actions = ai_service.extract_action_items(
            email_subject=self._current_thread.get("subject", ""),
            email_body=self._current_thread.get("body", "")
        )
        
        return {
            "type": "action_items",
            "actions": actions
        }
    
    def _handle_search(self) -> Dict[str, Any]:
        """Handle the AI search command."""
        if not self._selected_text:
            raise ValueError("No search query provided")
            
        results = ai_service.search_emails(
            query=self._selected_text,
            limit=10
        )
        
        return {
            "type": "search_results",
            "query": self._selected_text,
            "results": [{
                "id": r.id,
                "subject": r.subject,
                "snippet": r.snippet,
                "sender": r.sender,
                "date": r.date,
                "relevance": r.relevance
            } for r in results]
        }
