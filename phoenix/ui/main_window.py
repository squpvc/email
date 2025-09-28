"""
Main window for Project Phoenix.
"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QByteArray, QEvent
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPalette, QColor, QCloseEvent, QKeyEvent, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStatusBar, QToolBar, QLabel, QSizePolicy, QMessageBox, QDialog
)

from ..application_base import PhoenixApplicationBase

# Import widgets with conditional imports to avoid circular dependencies
if TYPE_CHECKING:
    from .dialogs.settings_dialog import SettingsDialog
    from .widgets.sidebar import Sidebar
    from .widgets.email_list import EmailList
    from .widgets.email_view import EmailView
    from .widgets.command_palette import CommandPalette
else:
    SettingsDialog = None
    Sidebar = None
    EmailList = None
    EmailView = None
    CommandPalette = None

from .themes import apply_theme


class MainWindow(QMainWindow):
    """Main application window."""
    
    # Signals
    toggle_sidebar_signal = pyqtSignal()
    
    # Window state keys
    WINDOW_GEOMETRY = "window/geometry"
    WINDOW_STATE = "window/state"
    SIDEBAR_VISIBLE = "ui/sidebar_visible"
    SPLITTER_STATE = "ui/splitter_state"
    
    def __init__(self, app: PhoenixApplicationBase):
        """Initialize the main window.
        
        Args:
            app: The main application instance
        """
        super().__init__()
        self.app = app
        self.logger = logging.getLogger(__name__)
        self._initializing = True
        
        # Initialize widget references that will be set up in _setup_ui
        self.sidebar: Optional[Sidebar] = None
        self.email_list: Optional[EmailList] = None
        self.email_view: Optional[EmailView] = None
        self.command_palette: Optional[CommandPalette] = None
        self.settings_dialog: Optional[SettingsDialog] = None
        
        # Window state
        self._sidebar_visible = True
        self._splitter_sizes = [200, 800]  # Default splitter sizes
        self._current_font_size = 9  # Default font size
        self._default_font_size = 9  # Default font size for reset
        self._font_size_step = 1     # Font size increment/decrement step
        self._min_font_size = 8      # Minimum allowed font size
        self._max_font_size = 24     # Maximum allowed font size
        
        # Initialize dialogs
        self.settings_dialog = None
        
        # Set up UI and connections
        self._setup_ui()
        self._setup_connections()
        
        # Load window state after UI is initialized
        self._load_window_state()
        self._initializing = False
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Import widgets here to avoid circular imports
        from .widgets.sidebar import Sidebar
        from .widgets.email_list import EmailList
        from .widgets.email_view import EmailView
        from .widgets.command_palette import CommandPalette
        
        # Main window properties
        self.setWindowTitle("Project Phoenix")
        self.setMinimumSize(800, 600)
        
        # Central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Content widget (sidebar + main content)
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Initialize sidebar
        self.sidebar = Sidebar()
        self.content_layout.addWidget(self.sidebar)
        
        # Main splitter (email list + email view)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(1)
        
        # Initialize email list
        self.email_list = EmailList()
        self.main_splitter.addWidget(self.email_list)
        
        # Initialize email view
        self.email_view = EmailView()
        self.main_splitter.addWidget(self.email_view)
        
        # Set initial splitter sizes
        self.main_splitter.setSizes([300, 500])
        
        self.content_layout.addWidget(self.main_splitter)
        self.main_layout.addWidget(self.content_widget)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Initialize command palette
        self.command_palette = CommandPalette(self)
        
        # Set initial window state
        self._load_window_state()
        
        # Connect signals
        self.sidebar.folder_selected.connect(self._on_folder_selected)
        self.email_list.email_selected.connect(self._on_email_selected)
        
        # Connect email action signals
        self.email_list.compose_requested.connect(self.compose_email)
        self.email_list.reply_requested.connect(self._on_reply_requested)
        self.email_list.forward_requested.connect(self._on_forward_requested)
        self.email_list.refresh_requested.connect(self._on_refresh_requested)
        
        # Initialize state
        self._current_folder = None
        self._selected_email = None
    
    def _setup_toolbar(self) -> None:
        """Set up the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Menu button
        menu_btn = toolbar.addAction("☰")
        menu_btn.triggered.connect(self.toggle_sidebar_signal.emit)
        
        # Add spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)
        
        # Settings button
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._show_settings)
        toolbar.addAction(settings_action)
        
        # Search bar
        search_action = QAction("Search...", self)
        search_action.setShortcut(QKeySequence.StandardKey.Find)
        search_action.triggered.connect(self.show_command_palette)
        toolbar.addAction(search_action)
        
        self.toolbar = toolbar
    
    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self.toggle_sidebar_signal.connect(self._on_toggle_sidebar)
        
        # Connect command palette shortcuts
        self.command_palette.activated.connect(self._on_command_activated)
    
    def _on_toggle_sidebar(self) -> None:
        """Handle sidebar toggle."""
        self.toggle_sidebar()
    
    def toggle_sidebar(self) -> None:
        """Toggle the sidebar visibility."""
        visible = not self.sidebar.isVisible()
        self.sidebar.setVisible(visible)
        self._save_window_state()
        
    def toggle_statusbar(self) -> None:
        """Toggle the status bar visibility."""
        self.statusBar().setVisible(not self.statusBar().isVisible())
        self._save_window_state()
        
    def show_new_event_dialog(self) -> None:
        """Show the new event dialog.
        
        This is a placeholder implementation that will be replaced with a proper
        calendar event dialog in the future.
        """
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "New Event",
            "This will show a dialog to create a new calendar event.\n\n"
            "This is a placeholder implementation. In a future update, this will open "
            "a dialog to create new calendar events with title, date/time, location, "
            "and other event details.",
            QMessageBox.StandardButton.Ok
        )
        
    def show_new_task_dialog(self) -> None:
        """Show the new task dialog.
        
        This is a placeholder implementation that will be replaced with a proper
        task management dialog in the future.
        """
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "New Task",
            "This will show a dialog to create a new task.\n\n"
            "This is a placeholder implementation. In a future update, this will open "
            "a dialog to create new tasks with title, due date, priority, and other "
            "task details.",
            QMessageBox.StandardButton.Ok
        )
        
    def complete_selected_task(self) -> None:
        """Mark the currently selected task as complete.
        
        This is a placeholder implementation that will be replaced with actual
        task completion logic in the future.
        """
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Complete Task",
            "This will mark the currently selected task as complete.\n\n"
            "This is a placeholder implementation. In a future update, this will "
            "update the task's status in the database and refresh the task list.",
            QMessageBox.StandardButton.Ok
        )
    
    def navigate_to(self, folder: str) -> None:
        """Navigate to a specific folder.
        
        Args:
            folder: The folder to navigate to (e.g., 'inbox', 'sent', 'drafts')
        """
        self.sidebar.select_folder(folder)
        self._current_folder = folder
        self._load_emails_for_folder(folder)
    
    def compose_email(self, to: str = "", subject: str = "", body: str = "") -> None:
        """Open the compose email dialog.
        
        Args:
            to: Recipient email address(es)
            subject: Email subject
            body: Email body content
        """
        # TODO: Implement compose email dialog
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, 
            "Compose Email", 
            f"Would compose email to: {to}\nSubject: {subject}\n\n{body}"
        )
    
    def reply_to_email(self, reply_all: bool = False) -> None:
        """Reply to the selected email.
        
        Args:
            reply_all: Whether to reply to all recipients
        """
        if not self._selected_email:
            self.show_status_message("No email selected")
            return
            
        # TODO: Implement reply functionality
        prefix = "Re: " if not self._selected_email.subject.lower().startswith("re: ") else ""
        subject = f"{prefix}{self._selected_email.subject}"
        
        # Get the original sender for reply-to
        to = self._selected_email.sender if not reply_all else ""
        
        self.compose_email(
            to=to,
            subject=subject,
            body=f"\n\n--- Original Message ---\n{self._selected_email.body}"
        )
    
    def get_selected_email(self):
        """Get the currently selected email."""
        return self._selected_email
    
    def show_summary_preview(self, summary: str) -> None:
        """Show a summary preview in the email view.
        
        Args:
            summary: The summary text to display
        """
        self.email_view.show_summary(summary)
    
    def show_reply_suggestion(self, suggestion: str) -> None:
        """Show a suggested reply in the compose window.
        
        Args:
            suggestion: The suggested reply text
        """
        self.email_view.set_suggested_reply(suggestion)
    
    def _on_folder_selected(self, folder: str) -> None:
        """Handle folder selection from sidebar."""
        self.navigate_to(folder)
    
    def _on_email_selected(self, email_data: dict) -> None:
        """Handle email selection from the email list."""
        self._selected_email = email_data
        self.email_view.set_email(email_data)
    
    def _on_reply_requested(self, email_data: dict, reply_all: bool = False) -> None:
        """Handle reply request from email list."""
        self.reply_to_email(reply_all)
    
    def _on_forward_requested(self, email_data: dict) -> None:
        """Handle forward request from email list."""
        self.forward_email(email_data)
    
    def _on_refresh_requested(self) -> None:
        """Handle refresh request from email list."""
        if self._current_folder:
            self._load_emails_for_folder(self._current_folder)
    
    def _load_emails_for_folder(self, folder: str) -> None:
        """Load emails for the specified folder.
        
        Args:
            folder: The folder to load emails from
        """
        self.email_list.clear()
        self.show_status_message(f"Loading {folder}...")
        
        # TODO: Load actual emails from database/email service
        # For now, use sample emails
        sample_emails = [
            {
                'id': f'email_{i}',
                'sender': f'sender{i}@example.com',
                'sender_email': f'sender{i}@example.com',
                'sender_name': f'Sender {i}',
                'subject': f'Sample Email {i}',
                'body': f'This is a sample email content {i}.',
                'body_text': f'This is a sample email content {i}.',
                'date': '2025-07-19T01:52:10+03:00',
                'to': [{'email': 'recipient@example.com', 'name': 'Recipient Name'}],
                'cc': [],
                'bcc': [],
                'attachments': [],
                'is_read': i % 3 == 0,  # Mark every 3rd email as read
                'is_starred': i % 5 == 0,  # Mark every 5th email as starred
                'folder': folder
            }
            for i in range(1, 11)  # Generate 10 sample emails
        ]
        
        self.email_list.populate(sample_emails)
        self.show_status_message(f"Loaded {len(sample_emails)} emails from {folder}")
        
        # If we have emails, select the first one
        if sample_emails:
            self._on_email_selected(sample_emails[0])
    
    def show_command_palette(self) -> None:
        """Show the command palette."""
        self.command_palette.show()
        self.command_palette.setFocus()
    
    def _on_command_activated(self, command: str) -> None:
        """Handle command palette activation."""
        # TODO: Implement command handling
        print(f"Command activated: {command}")
    
    def _load_window_state(self) -> None:
        """Load the saved window state and geometry."""
        try:
            # Restore window geometry and state
            if self.WINDOW_GEOMETRY in self.app.settings:
                self.restoreGeometry(QByteArray.fromHex(self.app.settings[self.WINDOW_GEOMETRY].encode()))
            if self.WINDOW_STATE in self.app.settings:
                self.restoreState(QByteArray.fromHex(self.app.settings[self.WINDOW_STATE].encode()))
            
            # Restore sidebar visibility
            sidebar_visible = self.app.settings.get(self.SIDEBAR_VISIBLE, "true").lower() == "true"
            self.sidebar.setVisible(sidebar_visible)
            
            # Restore splitter state
            if self.SPLITTER_STATE in self.app.settings:
                try:
                    sizes = json.loads(self.app.settings[self.SPLITTER_STATE])
                    if isinstance(sizes, list) and len(sizes) == 2:
                        self.main_splitter.setSizes(sizes)
                        self._splitter_sizes = sizes
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.warning(f"Invalid splitter state: {e}")
            
            self.logger.debug("Window state loaded")
        except Exception as e:
            self.logger.error(f"Error loading window state: {e}")
    
    def toggle_sidebar(self) -> None:
        """Toggle the sidebar visibility."""
        self._sidebar_visible = not self._sidebar_visible
        self.sidebar.setVisible(self._sidebar_visible)
        # Save state asynchronously
        asyncio.create_task(self._save_window_state())
    
    async def _save_window_state(self) -> None:
        """Save the current window state and geometry."""
        if self._initializing:
            return
            
        try:
            # Save window geometry and state
            await self.app._save_setting(self.WINDOW_GEOMETRY, self.saveGeometry().toHex().data().decode())
            await self.app._save_setting(self.WINDOW_STATE, self.saveState().toHex().data().decode())
            
            # Save sidebar visibility
            await self.app._save_setting(self.SIDEBAR_VISIBLE, str(self.sidebar.isVisible()).lower())
            
            # Save splitter state
            splitter_sizes = self.main_splitter.sizes()
            await self.app._save_setting(self.SPLITTER_STATE, json.dumps(splitter_sizes))
            
            self.logger.debug("Window state saved")
        except Exception as e:
            self.logger.error(f"Error saving window state: {e}")
    
    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """Handle splitter movement."""
        if not self._initializing:
            self._splitter_sizes = self.main_splitter.sizes()
            # Debounce the save operation
            if hasattr(self, '_splitter_timer'):
                self._splitter_timer.stop()
            else:
                self._splitter_timer = QTimer()
                self._splitter_timer.setSingleShot(True)
                self._splitter_timer.timeout.connect(
                    lambda: asyncio.create_task(self._save_window_state())
                )
            self._splitter_timer.start(500)  # Save after 500ms of inactivity
    
    async def _shutdown_application(self) -> None:
        """Helper method to properly shut down the application."""
        try:
            # Save window state before shutting down
            await self._save_window_state()
            
            # Schedule the shutdown coroutine
            await self.app.shutdown()
            return True
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            return False
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        # Schedule the shutdown coroutine
        asyncio.create_task(self._shutdown_application())
        
        # Accept the close event to allow the window to close
        event.accept()
        
        # The actual application shutdown will continue in the background
        # We've already saved the window state in _shutdown_application
    
    def showEvent(self, event) -> None:
        """Handle show event to ensure proper initialization."""
        super().showEvent(event)
        if not self._initializing:
            # Apply theme to all child widgets
            # Use QTimer.singleShot to avoid blocking the event loop
            from PyQt6.QtCore import QTimer
            
            def apply_theme():
                try:
                    import asyncio
                    # Run the coroutine in the event loop
                    if hasattr(self.app, '_loop') and self.app._loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            self.app.set_theme(self.app.theme),
                            self.app._loop
                        )
                except Exception as e:
                    self.logger.error(f"Error applying theme: {e}")
            
            # Schedule the theme application to run after the event loop starts
            QTimer.singleShot(0, apply_theme)
    
    def changeEvent(self, event) -> None:
        """Handle window state changes."""
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            # Save window state when maximized/restored
            asyncio.create_task(self._save_window_state())
    
    def _show_settings(self) -> None:
        """Show the settings dialog."""
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self.app, self)
            self.settings_dialog.settings_changed.connect(self._on_settings_changed)
        
        if self.settings_dialog.exec() == QDialog.DialogCode.Accepted:
            # Settings were saved
            pass
    
    def _on_settings_changed(self) -> None:
        """Handle settings changes."""
        # TODO: Implement settings change handling
        pass
        
    def increase_font_size(self) -> None:
        """Increase the application font size."""
        new_size = min(self._current_font_size + self._font_size_step, self._max_font_size)
        if new_size != self._current_font_size:
            self._current_font_size = new_size
            self._apply_font_size()
    
    def decrease_font_size(self) -> None:
        """Decrease the application font size."""
        new_size = max(self._current_font_size - self._font_size_step, self._min_font_size)
        if new_size != self._current_font_size:
            self._current_font_size = new_size
            self._apply_font_size()
    
    def reset_font_size(self) -> None:
        """Reset the application font size to default."""
        if self._current_font_size != self._default_font_size:
            self._current_font_size = self._default_font_size
            self._apply_font_size()
    
    def _apply_font_size(self) -> None:
        """Apply the current font size to the application."""
        font = self.font()
        font.setPointSize(self._current_font_size)
        self.setFont(font)
        
        # Update child widgets that need custom font handling
        self.email_list.setFont(font)
        self.email_view.setFont(font)
        self.sidebar.setFont(font)
        
        # Update status bar message
        self.statusBar.showMessage(f"Font size: {self._current_font_size}pt", 2000)
        self.app.qt_app.setFont(font)
        
        # Update UI elements as needed
        self.update()
