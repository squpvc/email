"""
Command palette commands for Project Phoenix.
"""
import logging
from typing import Callable, Dict, List, Optional, Any
from typing import Dict, List, Optional, Callable, Any, TYPE_CHECKING

from phoenix.models.command import Command, CommandCategory

from PyQt6.QtGui import QKeySequence
from PyQt6.QtCore import Qt, QObject, pyqtSignal

# Import AI commands if available
try:
    from ..ai.commands import AICommandHandler
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# Import Outlook import command
try:
    from ..commands.outlook_import import OutlookImportCommand
    OUTLOOK_IMPORT_AVAILABLE = True
except ImportError as e:
    OUTLOOK_IMPORT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Outlook import command not available: {e}")

# Command class moved to phoenix.models.command

class CommandRegistry:
    """Registry for command palette commands."""
    
    def __init__(self, app):
        self.app = app
        self._commands: Dict[str, Command] = {}
        self._ai_handler = AICommandHandler(app) if AI_AVAILABLE else None
        self._outlook_import_cmd = OutlookImportCommand() if OUTLOOK_IMPORT_AVAILABLE else None
        self._setup_default_commands()
        self._setup_ai_commands()
        self._setup_outlook_import_command()
        
        # Connect to main window's ready signal if available
        if hasattr(app, 'main_window') and app.main_window:
            self._connect_main_window_handlers()
    
    def _connect_main_window_handlers(self) -> None:
        """Connect handlers that depend on main window being available."""
        if not hasattr(self.app, 'main_window') or not self.app.main_window:
            return
            
        # Update email commands with actual handlers
        if hasattr(self.app.main_window, 'compose_email'):
            if 'compose_email' in self._commands:
                self._commands['compose_email'].handler = self.app.main_window.compose_email
                
        if hasattr(self.app.main_window, 'reply_to_email'):
            if 'reply_email' in self._commands:
                self._commands['reply_email'].handler = self.app.main_window.reply_to_email
                
        if hasattr(self.app.main_window, 'toggle_sidebar'):
            if 'toggle_sidebar' in self._commands:
                self._commands['toggle_sidebar'].handler = self.app.main_window.toggle_sidebar
    
    def _compose_email(self):
        """Handle compose email command when main window is not ready."""
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'compose_email'):
            self.app.main_window.compose_email()
        else:
            self.app.show_error_message("Email functionality is not available yet. Please wait for the application to fully load.")
    
    def _reply_to_email(self):
        """Handle reply to email command when main window is not ready."""
        if hasattr(self.app, 'main_window') and hasattr(self.app.main_window, 'reply_to_email'):
            self.app.main_window.reply_to_email()
        else:
            self.app.show_error_message("Email functionality is not available yet. Please wait for the application to fully load.")
    
    def _setup_ai_commands(self) -> None:
        """Set up AI-powered commands."""
        if not AI_AVAILABLE or not self._ai_handler:
            return
            
        for cmd in self._ai_handler.get_commands():
            self.add_command(
                command_id=cmd.id,
                name=cmd.name,
                handler=cmd.handler,
                shortcut="",  # AI commands typically don't have shortcuts
                category=cmd.category,
                description=cmd.description,
                keywords=cmd.keywords if hasattr(cmd, 'keywords') else []
            )
    
    def _setup_outlook_import_command(self) -> None:
        """Set up the Outlook import command if available."""
        if not OUTLOOK_IMPORT_AVAILABLE or not self._outlook_import_cmd:
            return
            
        # Add the Outlook import command
        self.add_command(
            command_id="import_outlook",
            name=self._outlook_import_cmd.name,
            handler=self._outlook_import_cmd.execute,
            shortcut=self._outlook_import_cmd.shortcut,
            category="Import/Export",
            description=self._outlook_import_cmd.description,
            keywords={"outlook", "import", "pst", "ost", "email", "migrate"}
        )
    
    def _setup_default_commands(self) -> None:
        """Set up default commands."""
        # Navigation commands
        self.add_command(
            id="navigate_inbox",
            name="Go to Inbox",
            handler=lambda: self.app.main_window.navigate_to("inbox") if hasattr(self.app, 'main_window') and self.app.main_window else None,
            shortcut="Ctrl+1",
            category="Navigation",
            description="Switch to the Inbox view"
        )
        
        self.add_command(
            id="navigate_sent",
            name="Go to Sent",
            handler=lambda: self.app.main_window.navigate_to("sent") if hasattr(self.app, 'main_window') and self.app.main_window else None,
            shortcut="Ctrl+2",
            category="Navigation",
            description="Switch to the Sent items view"
        )
        
        # Email actions - these will be registered but handlers will be set when main window is available
        self.add_command(
            id="compose_email",
            name="Compose Email",
            handler=self._compose_email,
            shortcut="Ctrl+N",
            category="Email",
            description="Compose a new email"
        )
        
        self.add_command(
            id="reply_email",
            name="Reply to Email",
            handler=self._reply_to_email,
            shortcut="Ctrl+R",
            category="Email",
            description="Reply to the selected email"
        )
        
        # View commands
        self.add_command(
            id="toggle_sidebar",
            name="Toggle Sidebar",
            handler=self.app.main_window.toggle_sidebar,
            shortcut="Ctrl+\\",
            category="View",
            description="Show or hide the sidebar"
        )
        
        self.add_command(
            id="toggle_theme",
            name="Toggle Theme",
            handler=self._toggle_theme,
            shortcut="Ctrl+Shift+T",
            category="View",
            description="Switch between light and dark themes"
        )
        
        # AI-powered commands
        self.add_command(
            id="summarize_email",
            name="Summarize Email",
            handler=self._summarize_email,
            shortcut="",
            category="AI",
            description="Generate a summary of the selected email"
        )
        
        self.add_command(
            id="suggest_reply",
            name="Suggest Reply",
            handler=self._suggest_reply,
            shortcut="",
            category="AI",
            description="Generate a suggested reply to the selected email"
        )
        
        # Settings
        self.add_command(
            id="open_settings",
            name="Open Settings",
            handler=self.app.main_window._show_settings,
            shortcut="Ctrl+,",
            category="Settings",
            description="Open application settings"
        )
        
        # Theme and Appearance
        self.add_command(
            id="toggle_theme",
            name="Toggle Dark/Light Theme",
            handler=self.app.theme_manager.toggle_theme,
            shortcut="Ctrl+Shift+T",
            category="Preferences",
            description="Switch between dark and light theme"
        )
        
        self.add_command(
            id="increase_font_size",
            name="Increase Font Size",
            handler=self.app.main_window.increase_font_size,
            shortcut="Ctrl++",
            category="Preferences",
            description="Increase the application font size"
        )
        
        self.add_command(
            id="decrease_font_size",
            name="Decrease Font Size",
            handler=self.app.main_window.decrease_font_size,
            shortcut="Ctrl+-",
            category="Preferences",
            description="Decrease the application font size"
        )
        
        self.add_command(
            id="reset_font_size",
            name="Reset Font Size",
            handler=self.app.main_window.reset_font_size,
            shortcut="Ctrl+0",
            category="Preferences",
            description="Reset font size to default"
        )
        
        # Notifications
        self.add_command(
            id="toggle_notifications",
            name="Toggle Notifications",
            handler=self.app.notification_manager.toggle_notifications,
            category="Preferences",
            description="Enable or disable desktop notifications"
        )
        
        # Layout
        self.add_command(
            id="toggle_sidebar",
            name="Toggle Sidebar",
            handler=self.app.main_window.toggle_sidebar,
            shortcut="Ctrl+\\",
            category="Layout",
            description="Show or hide the sidebar"
        )
        
        self.add_command(
            id="toggle_statusbar",
            name="Toggle Status Bar",
            handler=self.app.main_window.toggle_statusbar,
            category="Layout",
            description="Show or hide the status bar"
        )
        
        # Calendar commands
        self.add_command(
            id="calendar_new_event",
            name="New Calendar Event",
            handler=self.app.main_window.show_new_event_dialog,
            shortcut="Ctrl+Shift+E",
            category="Calendar",
            description="Create a new calendar event"
        )
        
        self.add_command(
            id="calendar_view_day",
            name="View Day",
            handler=lambda: self.app.main_window.calendar_view.show_day_view(),
            shortcut="Ctrl+1",
            category="Calendar",
            description="Switch to day view in calendar"
        )
        
        self.add_command(
            id="calendar_view_week",
            name="View Week",
            handler=lambda: self.app.main_window.calendar_view.show_week_view(),
            shortcut="Ctrl+2",
            category="Calendar",
            description="Switch to week view in calendar"
        )
        
        self.add_command(
            id="calendar_view_month",
            name="View Month",
            handler=lambda: self.app.main_window.calendar_view.show_month_view(),
            shortcut="Ctrl+3",
            category="Calendar",
            description="Switch to month view in calendar"
        )
        
        # Task management commands
        self.add_command(
            id="task_new",
            name="New Task",
            handler=self.app.main_window.show_new_task_dialog,
            shortcut="Ctrl+T",
            category="Tasks",
            description="Create a new task"
        )
        
        self.add_command(
            id="task_complete",
            name="Complete Task",
            handler=self.app.main_window.complete_selected_task,
            shortcut="Ctrl+Enter",
            category="Tasks",
            description="Mark the selected task as complete"
        )
        
        self.add_command(
            id="task_show_all",
            name="Show All Tasks",
            handler=lambda: self.app.main_window.task_view.show_all_tasks(),
            category="Tasks",
            description="Show all tasks including completed ones"
        )
        
        self.add_command(
            id="task_hide_completed",
            name="Hide Completed Tasks",
            handler=lambda: self.app.main_window.task_view.hide_completed_tasks(),
            category="Tasks",
            description="Hide completed tasks"
        )
        
        # Calendar sync commands (if calendar integration is enabled)
        if hasattr(self.app, 'calendar_manager') and self.app.calendar_manager.is_connected():
            self.add_command(
                id="calendar_sync_now",
                name="Sync Calendar Now",
                handler=self.app.calendar_manager.sync,
                category="Calendar",
                description="Synchronize calendar with remote server"
            )
    
    def add_command(
        self,
        id: str,
        name: str,
        handler: Callable,
        shortcut: str = "",
        icon: str = "",
        category: str = "General",
        description: str = "",
        keywords: List[str] = None
    ) -> None:
        """Add a command to the registry.
        
        Args:
            id: Unique identifier for the command
            name: Display name of the command
            handler: Function to call when the command is executed
            shortcut: Keyboard shortcut (e.g., "Ctrl+K")
            icon: Icon name (from theme or resource)
            category: Category for grouping commands
            description: Detailed description of the command
            keywords: Additional search keywords for the command
        """
        if keywords is None:
            keywords = []
        
        # Create the command with proper keyword handling
        cmd_keywords = set(keywords) if keywords else set()
        cmd_keywords.update(term.lower() for term in name.split())
        cmd_keywords.update(term.lower() for term in description.split())
        cmd_keywords.add(category.lower())
        
        if shortcut:
            # Add shortcut terms without modifiers
            shortcut_terms = shortcut.replace('+', ' ').lower().split()
            cmd_keywords.update(term for term in shortcut_terms if len(term) > 1)
        
        command = Command(
            id=id,
            name=name,
            handler=handler,
            shortcut=shortcut,
            icon=icon,
            category=category,
            description=description,
            keywords=cmd_keywords
        )
        self._commands[id] = command
    
    def get_command(self, command_id: str) -> Optional[Command]:
        """Get a command by ID."""
        return self._commands.get(command_id)
    
    def get_commands(self) -> List[Command]:
        """Get all commands."""
        return list(self._commands.values())
    
    def _toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        new_theme = "dark" if self.app._theme == "light" else "light"
        # Schedule the coroutine to run in the event loop
        if hasattr(self.app, '_loop') and self.app._loop.is_running():
            asyncio.create_task(self.app.set_theme(new_theme))
        else:
            # Fallback in case the event loop isn't available
            import asyncio
            asyncio.run(self.app.set_theme(new_theme))
    
    def _summarize_email(self) -> None:
        """Generate a summary of the selected email using AI."""
        try:
            # Get the selected email
            selected_email = self.app.main_window.get_selected_email()
            if not selected_email:
                self.app.show_status_message("No email selected")
                return
                
            # Show loading state
            self.app.show_status_message("Generating summary...")
            
            # Generate summary (placeholder - integrate with AI service)
            summary = f"Summary of email from {selected_email.sender}: {selected_email.subject[:50]}..."
            
            # Show summary in a dialog or preview panel
            self.app.main_window.show_summary_preview(summary)
            
        except Exception as e:
            self.app.show_error_message(f"Error generating summary: {str(e)}")
    
    def _suggest_reply(self) -> None:
        """Generate a suggested reply to the selected email using AI."""
        try:
            # Get the selected email
            selected_email = self.app.main_window.get_selected_email()
            if not selected_email:
                self.app.show_status_message("No email selected")
                return
                
            # Show loading state
            self.app.show_status_message("Generating reply suggestion...")
            
            # Generate reply suggestion (placeholder - integrate with AI service)
            suggestion = f"Thank you for your email about {selected_email.subject[:30]}..."
            
            # Show suggestion in the compose window
            self.app.main_window.show_reply_suggestion(suggestion)
            
        except Exception as e:
            self.app.show_error_message(f"Error generating reply suggestion: {str(e)}")

    def search_commands(self, query: str) -> List[Command]:
        """Search commands by query."""
        if not query:
            return self.get_commands()
            
        query = query.lower()
        results = []
        
        for cmd in self._commands.values():
            # Check name, category, description, and keywords
            if (query in cmd.name.lower() or 
                query in cmd.category.lower() or 
                query in cmd.description.lower() or
                any(query in kw for kw in cmd.keywords)):
                results.append(cmd)
                
        return sorted(results, key=lambda x: (
            x.name.lower().startswith(query),  # Exact name matches first
            x.category.lower() == query,      # Then exact category matches
            -len(x.keywords)                  # Then commands with more keywords
        ), reverse=True)
