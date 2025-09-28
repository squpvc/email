"""
AI-powered commands for Project Phoenix.
"""
import logging
import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum, auto

from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QMessageBox, QInputDialog, QProgressDialog, QApplication
)

from .services import ai_service, AI_AVAILABLE, EmailSummary

if AI_AVAILABLE:
    from ..ui.widgets.search_results import SearchResultsDialog
    from ..ui.widgets.ai_assistant import AIAssistantDialog

# Configure logging
logger = logging.getLogger(__name__)

class AICommandType(Enum):
    """Types of AI commands."""
    EMAIL = auto()
    CALENDAR = auto()
    TASK = auto()
    GENERAL = auto()

@dataclass
class AICommand:
    """Represents an AI-powered command."""
    id: str
    name: str
    handler: Callable
    description: str
    category: str = "AI"
    icon: str = "ai"
    requires_ai: bool = True
    command_type: str = "general"
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        # Add name and description terms to keywords for better search
        self.keywords.extend([self.name.lower(), *self.description.lower().split()])

class AICommandSignals(QObject):
    """Signals for AI command execution."""
    command_started = pyqtSignal(str)  # command_id
    command_finished = pyqtSignal(str, bool)  # command_id, success
    progress_updated = pyqtSignal(int, str)  # progress_percent, status_message

class AICommandHandler:
    """Handler for AI-powered commands."""
    
    def __init__(self, app):
        self.app = app
        self.signals = AICommandSignals()
        self._last_executed = {}
        self._setup_commands()
        
        # Connect signals
        self.signals.command_started.connect(self._on_command_started)
        self.signals.command_finished.connect(self._on_command_finished)
    
    def _on_command_started(self, command_id: str) -> None:
        """Handle command start event."""
        logger.info(f"AI command started: {command_id}")
        self._last_executed[command_id] = datetime.datetime.now()
        
    def _on_command_finished(self, command_id: str, success: bool) -> None:
        """Handle command completion event."""
        status = "succeeded" if success else "failed"
        logger.info(f"AI command {command_id} {status}")
        
    def _setup_commands(self) -> None:
        """Set up AI commands with enhanced metadata."""
        self.commands = [
            # Email-related commands
            AICommand(
                id="ai_summarize_email",
                name="Summarize Email",
                handler=self.summarize_email,
                description="Generate a concise summary of the selected email",
                command_type="email",
                keywords=["brief", "overview", "main points"]
            ),
            AICommand(
                id="ai_suggest_reply",
                name="Suggest Reply",
                handler=self.suggest_reply,
                description="Generate a suggested reply to the selected email",
                command_type="email",
                keywords=["response", "draft", "answer"]
            ),
            AICommand(
                id="ai_search_emails",
                name="Search Emails",
                handler=self.search_emails,
                description="Search emails using natural language",
                command_type="email",
                keywords=["find", "locate", "discover"]
            ),
            AICommand(
                id="ai_prioritize_inbox",
                name="Prioritize Inbox",
                handler=self.prioritize_inbox,
                description="Show the most important emails that need attention",
                command_type="email",
                keywords=["important", "urgent", "unread"]
            ),
            
            # New AI Commands
            AICommand(
                id="ai_classify_email",
                name="Classify Email",
                handler=self.classify_email,
                description="Categorize and tag the selected email",
                command_type="email",
                keywords=["categorize", "tag", "organize"]
            ),
            AICommand(
                id="ai_schedule_followup",
                name="Schedule Follow-up",
                handler=self.schedule_followup,
                description="Schedule a follow-up for this email",
                command_type="calendar",
                keywords=["reminder", "follow up", "schedule"]
            ),
            AICommand(
                id="ai_extract_action_items",
                name="Extract Action Items",
                handler=self.extract_action_items,
                description="Extract action items from the email thread",
                command_type="task",
                keywords=["todo", "tasks", "actionable"]
            ),
            AICommand(
                id="ai_improve_writing",
                name="Improve Writing",
                handler=self.improve_writing,
                description="Enhance the clarity and tone of your text",
                command_type="general",
                keywords=["rewrite", "enhance", "polish"]
            )
        ]
    
    def get_commands(self) -> List[AICommand]:
        """Get all AI commands, filtering based on availability."""
        if not AI_AVAILABLE:
            return [cmd for cmd in self.commands if not cmd.requires_ai]
        return self.commands
        
    def get_command(self, command_id: str) -> Optional[AICommand]:
        """Get a specific AI command by ID."""
        return next((cmd for cmd in self.commands if cmd.id == command_id), None)
        
    def get_commands_by_type(self, command_type: str) -> List[AICommand]:
        """Get commands filtered by type."""
        return [cmd for cmd in self.commands if cmd.command_type == command_type]
        
    def get_recent_commands(self, limit: int = 5) -> List[AICommand]:
        """Get recently used commands, most recent first."""
        recent = sorted(
            ((cmd_id, ts) for cmd_id, ts in self._last_executed.items() if ts),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        return [self.get_command(cmd_id) for cmd_id, _ in recent]
    
    def _execute_with_progress(self, command_id: str, task: Callable, *args, **kwargs) -> None:
        """Execute a task with progress indication."""
        self.signals.command_started.emit(command_id)
        
        # Create progress dialog
        progress = QProgressDialog("Processing...", "Cancel", 0, 0, self.app.main_window)
        progress.setWindowTitle("AI Assistant")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(1000)  # Show after 1 second
        
        def update_progress(percent: int, message: str) -> None:
            progress.setValue(percent)
            progress.setLabelText(message)
            QApplication.processEvents()
            
        def task_wrapper():
            try:
                result = task(update_progress, *args, **kwargs)
                self.signals.command_finished.emit(command_id, True)
                return result
            except Exception as e:
                logger.error(f"Command {command_id} failed: {str(e)}", exc_info=True)
                self.signals.command_finished.emit(command_id, False)
                self.app.show_error_message(f"Error: {str(e)}")
                return None
            finally:
                progress.close()
        
        # Start task in background
        QTimer.singleShot(0, task_wrapper)
    
    def summarize_email(self) -> None:
        """Generate a summary of the selected email with enhanced features."""
        if not AI_AVAILABLE:
            self._show_ai_not_available()
            return
            
        email = self.app.main_window.get_selected_email()
        if not email:
            self.app.show_error_message("No email selected")
            return
            
        def process(update_progress):
            update_progress(10, "Analyzing email content...")
            
            # Get email context
            thread = self.app.email_manager.get_email_thread(email.thread_id)
            update_progress(30, "Processing email thread...")
            
            # Generate summary
            update_progress(60, "Generating summary...")
            summary = ai_service.summarize_email(
                subject=email.subject,
                body=email.body,
                thread_context=thread,
                style="concise"  # Can be 'concise', 'detailed', or 'bullets'
            )
            
            update_progress(90, "Formatting results...")
            return summary
            
        def on_complete(summary):
            if summary:
                self.app.main_window.show_summary_preview(summary.summary)
                self.app.show_status_message("Summary generated")
        
        # Execute with progress tracking
        self._execute_with_progress("ai_summarize_email", process, on_complete)
    
    def suggest_reply(self) -> None:
        """Generate a suggested reply to the selected email."""
        if not AI_AVAILABLE:
            self._show_ai_not_available()
            return
            
        email = self.app.main_window.get_selected_email()
        if not email:
            self.app.show_error_message("No email selected")
            return
            
        # Show loading state
        self.app.show_status_message("Generating reply suggestion...")
        
        # Run in background to avoid UI freeze
        def _process_suggestion():
            try:
                suggestion = ai_service.suggest_reply(
                    email_subject=email.subject,
                    email_body=email.body
                )
                self.app.main_window.show_reply_suggestion(suggestion)
                self.app.show_status_message("Reply suggestion generated")
            except Exception as e:
                self.app.show_error_message(f"Error generating reply: {str(e)}")
        
        QTimer.singleShot(0, _process_suggestion)
    
    def search_emails(self, query: str = "") -> None:
        """Search emails using natural language."""
        if not AI_AVAILABLE:
            self._show_ai_not_available()
            return
            
        # If no query provided, show a dialog to enter search terms
        if not query:
            from PyQt6.QtWidgets import QInputDialog
            query, ok = QInputDialog.getText(
                self.app.main_window,
                "Search Emails",
                "Enter your search query:"
            )
            if not ok or not query.strip():
                return
        
        self.app.show_status_message(f"Searching for: {query}")
        
        # Run in background to avoid UI freeze
        def _process_search():
            try:
                results = ai_service.search_emails(query)
                if not results:
                    self.app.show_status_message("No matching emails found")
                    return
                    
                # Show results in a dialog
                dialog = SearchResultsDialog(
                    self.app.main_window,
                    results,
                    title=f"Search: {query}"
                )
                dialog.email_selected.connect(self.app.main_window.show_email)
                dialog.exec()
                
                self.app.show_status_message(f"Found {len(results)} results")
                
            except Exception as e:
                self.app.show_error_message(f"Error searching emails: {str(e)}")
        
        QTimer.singleShot(0, _process_search)
    
    def prioritize_inbox(self) -> None:
        """Show the most important emails that need attention."""
        if not AI_AVAILABLE:
            self._show_ai_not_available()
            return
            
        self.app.show_status_message("Analyzing inbox for important emails...")
        
        # Run in background to avoid UI freeze
        def _process_priority():
            try:
                # This would use more sophisticated logic in a real implementation
                results = ai_service.search_emails(
                    "important OR urgent OR action required",
                    n_results=10
                )
                
                if not results:
                    self.app.show_status_message("No important emails found")
                    return
                    
                # Show results in a dialog
                dialog = SearchResultsDialog(
                    self.app.main_window,
                    results,
                    title="Important Emails"
                )
                dialog.email_selected.connect(self.app.main_window.show_email)
                dialog.exec()
                
                self.app.show_status_message(f"Found {len(results)} important emails")
                
            except Exception as e:
                self.app.show_error_message(f"Error analyzing inbox: {str(e)}")
        
        QTimer.singleShot(0, _process_priority)
    
    # New AI Command Handlers
    def classify_email(self) -> None:
        """Classify and tag the selected email."""
        if not AI_AVAILABLE:
            self._show_ai_not_available()
            return
            
        email = self.app.main_window.get_selected_email()
        if not email:
            self.app.show_error_message("No email selected")
            return
            
        def process(update_progress):
            update_progress(20, "Analyzing email content...")
            
            # Get classification from AI service
            classification = ai_service.classify_email(
                subject=email.subject,
                body=email.body,
                sender=email.sender,
                recipients=email.recipients
            )
            
            update_progress(80, "Preparing results...")
            return classification
            
        def on_complete(classification):
            if classification:
                self.app.main_window.show_classification_results(classification)
                self.app.show_status_message("Email classified successfully")
        
        self._execute_with_progress("ai_classify_email", process, on_complete)
    
    def schedule_followup(self) -> None:
        """Schedule a follow-up for the selected email."""
        if not AI_AVAILABLE:
            self._show_ai_not_available()
            return
            
        email = self.app.main_window.get_selected_email()
        if not email:
            self.app.show_error_message("No email selected")
            return
            
        # Show dialog to get follow-up details
        from ..ui.dialogs import FollowUpDialog
        dialog = FollowUpDialog(email, self.app.main_window)
        if dialog.exec():
            followup_details = dialog.get_followup_details()
            
            def process(update_progress):
                update_progress(30, "Scheduling follow-up...")
                # Create calendar event and set reminder
                event_id = self.app.calendar_manager.create_followup_event(
                    email=email,
                    when=followup_details['when'],
                    notes=followup_details['notes']
                )
                return event_id
                
            def on_complete(event_id):
                if event_id:
                    self.app.show_status_message("Follow-up scheduled")
                    # Optionally show the calendar event
                    self.app.main_window.show_calendar_event(event_id)
            
            self._execute_with_progress("ai_schedule_followup", process, on_complete)
    
    def extract_action_items(self) -> None:
        """Extract action items from the email thread."""
        if not AI_AVAILABLE:
            self._show_ai_not_available()
            return
            
        email = self.app.main_window.get_selected_email()
        if not email:
            self.app.show_error_message("No email selected")
            return
            
        def process(update_progress):
            update_progress(20, "Analyzing email thread...")
            
            # Get full thread
            thread = self.app.email_manager.get_email_thread(email.thread_id)
            update_progress(50, "Extracting action items...")
            
            # Extract action items
            action_items = ai_service.extract_action_items(
                thread=thread,
                current_user=self.app.current_user.email
            )
            
            update_progress(90, "Preparing results...")
            return action_items
            
        def on_complete(action_items):
            if action_items:
                self.app.main_window.show_action_items(action_items)
                self.app.show_status_message(f"Extracted {len(action_items)} action items")
        
        self._execute_with_progress("ai_extract_action_items", process, on_complete)
    
    def improve_writing(self) -> None:
        """Improve the clarity and tone of selected text."""
        if not AI_AVAILABLE:
            self._show_ai_not_available()
            return
            
        # Get selected text from the current editor
        editor = self.app.main_window.get_current_editor()
        if not editor:
            self.app.show_error_message("No text editor is active")
            return
            
        selected_text = editor.get_selected_text()
        if not selected_text.strip():
            self.app.show_error_message("No text selected")
            return
            
        # Show dialog to select improvement style
        styles = ["More Professional", "More Concise", "More Formal", "More Friendly"]
        style, ok = QInputDialog.getItem(
            self.app.main_window,
            "Improve Writing",
            "Select improvement style:",
            styles,
            0,  # Default to first item
            False  # Not editable
        )
        
        if not ok or not style:
            return
            
        def process(update_progress):
            update_progress(20, "Analyzing text...")
            
            # Get improved version from AI
            improved_text = ai_service.improve_text(
                text=selected_text,
                style=style.lower().replace(" ", "_")
            )
            
            update_progress(90, "Preparing results...")
            return improved_text
            
        def on_complete(improved_text):
            if improved_text:
                # Show diff view or replace selected text
                self.app.main_window.show_text_comparison(selected_text, improved_text)
                self.app.show_status_message("Text improvement complete")
        
        self._execute_with_progress("ai_improve_writing", process, on_complete)
    
    def _show_ai_not_available(self) -> None:
        """Show a message that AI features are not available."""
        QMessageBox.warning(
            self.app.main_window,
            "AI Features Not Available",
            "AI features require additional dependencies. "
            "Please install the required packages and restart the application.\n\n"
            "Run: pip install spacy sentence-transformers chromadb openai\n"
            "Also ensure you have set up your OpenAI API key in the settings."
        )
