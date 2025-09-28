"""
Main application class for Project Phoenix.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Type, Callable, TYPE_CHECKING

# Set up logger at module level
logger = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QApplication, QMessageBox, QStatusBar, QWidget, QMainWindow
)
from PyQt6.QtCore import (
    QObject, pyqtSignal, QTimer, QSettings, Qt, QSize, QPoint, 
    QRect, QByteArray, QUrl, QEvent, QThread, QMutex, QWaitCondition, 
    QThreadPool, QRunnable, QCoreApplication, QMetaObject, Q_ARG, pyqtSlot
)
from PyQt6.QtGui import (
    QIcon, QFont, QColor, QPalette, QKeySequence, QFontDatabase, QShortcut
)

# Import command palette
from .ui.widgets.command_palette import CommandPalette, CommandItem
from .application_base import PhoenixApplicationBase

from .config import APP_NAME, APP_VERSION, APP_AUTHOR, CONFIG_DIR, CACHE_DIR, LOG_FILE, DATA_DIR, LOG_DIR
from .database import DatabaseManager
from .ui.commands import CommandRegistry
from .utils.logging import setup_logging
from .utils.theme import ThemeManager, apply_theme, get_theme_names
from .utils.notifications import NotificationManager

# Import AI services
from .ai.services import ai_service, AI_AVAILABLE

# Import MainWindow with a lazy import pattern to avoid circular imports
class LazyMainWindow:
    def __getattr__(self, name):
        from .ui.main_window import MainWindow
        return getattr(MainWindow, name)

# Use lazy loading for MainWindow to avoid circular imports
MainWindow = LazyMainWindow()

class PhoenixApplication(PhoenixApplicationBase, QObject):
    """Main application class for Project Phoenix."""
    
    # Signals
    shutdown_signal = pyqtSignal()
    
    def __init__(self, argv):
        """Initialize the application."""
        super().__init__()
        self.args = argv
        self._qt_app = QApplication(argv)
        self._qt_app.setQuitOnLastWindowClosed(True)
        
        # Initialize paths
        self.app_dir = Path(__file__).parent.parent
        
        # Set up logging
        setup_logging(LOG_FILE)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
        
        # Initialize database
        self.db = DatabaseManager()
        
        # Initialize theme manager
        self.theme_manager = ThemeManager(self._qt_app)
        self._theme = "light"  # Default theme
        
        # Initialize notification manager
        self.notification_manager = NotificationManager(self)
        
        # Initialize AI services if available
        self.ai_service = ai_service if AI_AVAILABLE else None
        if not AI_AVAILABLE:
            self.logger.warning("AI features are not available. Some functionality will be limited.")
        
        # Initialize main window
        self._main_window: Optional[MainWindow] = None
        
        # Initialize settings dictionary
        self.settings = {}
        self._load_settings()
        
        # Set up application-wide styles
        self.setup_styles()
        
        # Initialize command registry (will be set up after main window is created)
        self._command_registry = None
        self._command_palette = None  # Will be initialized in initialize_ui
        
        # Show main window after event loop starts
        QTimer.singleShot(0, self.initialize_ui)
        
        # Set up signal handlers
        self.shutdown_signal.connect(self.shutdown)
        
        # Set up global shortcut for command palette
        self._command_palette_shortcut = QShortcut(QKeySequence("Ctrl+K"), self._qt_app)
        self._command_palette_shortcut.activated.connect(self.show_command_palette)
        
        # Background tasks
        self._background_tasks = set()
        self._shutting_down = False
        
        # Set up async event loop and periodic tasks
        self._setup_periodic_tasks()
    
    def initialize_ui(self) -> None:
        """Initialize the user interface."""
        try:
            # Import MainWindow here to avoid circular imports
            from .ui.main_window import MainWindow
            
            # Create main window
            self._main_window = MainWindow(self)
            
            # Initialize command registry after main window is created
            self._command_registry = CommandRegistry(self)
            
            # Set up command palette
            self._setup_command_palette()
            
            # Show main window
            self._main_window.show()
            
            # Initialize theme
            self.theme_manager.apply_theme()
            
        except Exception as e:
            self.logger.exception("Failed to initialize UI")
            QMessageBox.critical(
                None,
                "Initialization Error",
                f"Failed to initialize application: {str(e)}"
            )
            self.shutdown()
    
    def show_command_palette(self) -> None:
        """Show the command palette."""
        if not self._command_palette:
            return
            
        # Update command list in case commands were added/removed
        self._command_palette.clear_commands()
        for cmd in self._command_registry.get_commands():
            self._command_palette.add_command(
                command_id=cmd.id,
                name=cmd.name,
                handler=cmd.handler,
                shortcut=cmd.shortcut,
                icon=cmd.icon,
                category=cmd.category,
                description=cmd.description
            )
            
        # Position near the mouse or centered on the active window
        self._command_palette.show()
        self._command_palette.raise_()
        self._command_palette.activateWindow()
    
    def _setup_command_palette(self) -> None:
        """Set up the command palette with registered commands."""
        if not self.main_window:
            return
            
        self._command_palette = CommandPalette(self.main_window)
        
        # Connect signals
        self._command_palette.activated.connect(self._on_command_activated)
        self._command_palette.command_triggered.connect(self._on_command_triggered)
        
        # Add all registered commands to the palette
        for cmd in self._command_registry.get_commands():
            # Create a CommandItem and add it to the palette's _commands dictionary
            command_item = CommandItem(
                id=cmd.id,
                name=cmd.name,
                handler=cmd.handler,
                shortcut=cmd.shortcut,
                icon=cmd.icon,
                category=cmd.category,
                description=cmd.description
            )
            self._command_palette._commands[cmd.id] = command_item
            
            # Add category to the set of categories
            if cmd.category:
                self._command_palette._categories.add(cmd.category)
                
        # Update the command list in the UI
        self._command_palette._update_commands()
        
        # Add global shortcuts to show command palette
        QShortcut(QKeySequence("Ctrl+K"), self._qt_app, self.show_command_palette)
        QShortcut(QKeySequence("Ctrl+P"), self._qt_app, self.show_command_palette)
    
    def _on_command_activated(self, command_id: str) -> None:
        """Handle command activation from the command palette.
        
        Args:
            command_id: The ID of the command that was activated
        """
        try:
            command = self._command_registry.get_command(command_id)
            if command and command.handler:
                command.handler()
        except Exception as e:
            self.logger.error(f"Error executing command {command_id}: {str(e)}")
            self.show_error_message(f"Error executing command: {str(e)}")
    
    def _on_command_triggered(self, command) -> None:
        """Handle command execution from the command palette."""
        try:
            command.handler()
        except Exception as e:
            self.show_error_message(f"Error executing command: {str(e)}")
    
    def show_command_palette(self) -> None:
        """Show the command palette."""
        if not self._command_palette and self.main_window:
            self._setup_command_palette()
            
        if self._command_palette:
            self._command_palette.show()
            self._command_palette.raise_()
            self._command_palette.activateWindow()
    
    def show_status_message(self, message: str, timeout: int = 3000) -> None:
        """Show a status message in the main window's status bar.
        
        Args:
            message: The message to display
            timeout: How long to show the message in milliseconds (0 = until next message)
        """
        if self.main_window and hasattr(self.main_window, 'statusBar'):
            status_bar = self.main_window.statusBar()
            if status_bar:
                status_bar.showMessage(message, timeout)
    
    def show_error_message(self, message: str, title: str = "Error") -> None:
        """Show an error message dialog.
        
        Args:
            message: The error message to display
            title: The dialog title (default: "Error")
        """
        QMessageBox.critical(
            self.main_window if self.main_window else None,
            title,
            message,
            QMessageBox.StandardButton.Ok
        )
    
    def _setup_periodic_tasks(self) -> None:
        """Set up periodic background tasks."""
        # Create a new event loop for this thread if one doesn't exist
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        # Setup a timer to run the asyncio event loop
        self._timer = QTimer()
        self._timer.timeout.connect(self._process_asyncio_events)
        self._timer.start(50)  # Run every 50ms
        
        # Start the asyncio event loop in the main thread
        # We'll use a single event loop for the entire application
        if not hasattr(self, '_loop_task') or (hasattr(self, '_loop_task') and self._loop_task.done()):
            # Schedule the keep-alive coroutine to run on the event loop
            self._loop.call_soon_threadsafe(
                lambda: self._loop.create_task(self._keep_alive())
            )
    
    async def _keep_alive(self) -> None:
        """Keep the asyncio event loop running."""
        while not self._shutting_down:
            await asyncio.sleep(1)
    
    def _process_asyncio_events(self) -> None:
        """Process asyncio events in the Qt event loop."""
        if not hasattr(self, '_loop') or self._loop.is_closed() or self._shutting_down:
            return
            
        # Check if the event loop is already running
        if self._loop.is_running():
            # If the loop is already running, just schedule a no-op callback
            # to ensure pending tasks are processed
            self._loop.call_soon(lambda: None)
        else:
            # If the loop is not running, run it until all tasks are done
            try:
                # Process any pending asyncio tasks
                self._loop.stop()
                self._loop.run_forever()
            except Exception as e:
                if not self._shutting_down:  # Don't log errors during shutdown
                    logger.error(f"Error in asyncio event loop: {e}", exc_info=True)
    
    def _background_task(self, coro) -> asyncio.Task:
        """Run a coroutine in the background."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task
    
    async def initialize(self) -> None:
        """Initialize the application asynchronously."""
        logger.info("Initializing Project Phoenix...")
        
        # Ensure directories exist
        for directory in [CONFIG_DIR, DATA_DIR, LOG_DIR]:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        await self.db.initialize()
        
        # Load settings
        await self._load_settings()
        
        # Initialize UI
        await self._init_ui()
        
        # Initialize background services
        await self._init_background_services()
        
        logger.info("Project Phoenix initialized successfully")
    
    async def run(self) -> int:
        """Run the application."""
        try:
            await self.initialize()
            return self._qt_app.exec()
        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
            return 1
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shut down the application gracefully."""
        if self._shutting_down:
            return
            
        self._shutting_down = True
        logger.info("Shutting down Project Phoenix...")
        
        # Stop the timer
        if hasattr(self, '_timer') and self._timer.isActive():
            self._timer.stop()
        
        # Cancel all background tasks
        if hasattr(self, '_background_tasks'):
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        
        # Stop the asyncio event loop tasks
        if hasattr(self, '_loop_task') and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        
        # Close database connections
        if hasattr(self, 'db'):
            await self.db.close()
        
        # Stop the Qt application
        if hasattr(self, '_qt_app'):
            self._qt_app.quit()
        
        logger.info("Project Phoenix has been shut down")
    
    @property
    def qt_app(self) -> QApplication:
        """Get the underlying QApplication instance."""
        return self._qt_app
        
    @property
    def main_window(self) -> 'MainWindow':
        """Get the main window instance."""
        return self._main_window
        
    @property
    def theme(self) -> str:
        """Get the current theme name."""
        return self._theme
        
    def set_theme(self, theme_name: str) -> None:
        """Set the application theme synchronously.
        
        Args:
            theme_name: Name of the theme to apply
        """
        if theme_name not in get_theme_names():
            logger.warning(f"Unknown theme: {theme_name}")
            theme_name = "light"
            
        self._theme = theme_name
        apply_theme(self._qt_app, theme_name)
        
        # Save theme preference in the background
        if hasattr(self, '_qt_app') and hasattr(self, '_background_task'):
            self._background_task(self._save_setting("app/theme", theme_name))
    
    async def set_theme_async(self, theme_name: str) -> None:
        """Set the application theme asynchronously.
        
        Args:
            theme_name: Name of the theme to apply
        """
        if theme_name not in get_theme_names():
            logger.warning(f"Unknown theme: {theme_name}")
            theme_name = "light"
            
        self._theme = theme_name
        apply_theme(self._qt_app, theme_name)
        
        # Save theme preference
        await self._save_setting("app/theme", theme_name)
    
    def _load_settings(self) -> None:
        """Load application settings from the database."""
        try:
            # Initialize settings dictionary
            self.settings = {}
            
            try:
                # First ensure the settings table exists - use synchronous execute
                self.db.execute_sync("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                
                # Then try to load settings - use synchronous fetch
                settings = self.db.fetch_all_sync("SELECT key, value FROM settings")
                self.settings = {row[0]: row[1] for row in settings}
                
                # Apply saved theme or default
                theme = self.settings.get("app/theme", "light")
                if theme not in get_theme_names():
                    theme = "light"
                self._theme = theme
                
                logger.info(f"Loaded application settings: {len(self.settings)} settings")
                
            except Exception as db_error:
                logger.error(f"Database error loading settings: {db_error}", exc_info=True)
                # If we can't load settings, use defaults
                self.settings = {}
                self._theme = "light"
                
            # Apply the theme
            self.set_theme(self._theme)
            
        except Exception as e:
            logger.error(f"Failed to load settings: {e}", exc_info=True)
            # Fall back to default theme
            self._theme = "light"
            self.settings = {}
    
    async def _save_setting(self, key: str, value: Any) -> None:
        """Save a setting to the database.
        
        Args:
            key: Setting key
            value: Setting value (will be converted to string)
        """
        try:
            # First, check if the settings table exists
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Now insert or update the setting
            await self.db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (:key, :value)",
                key=key,
                value=str(value)
            )
            
            # Update the in-memory settings
            if not hasattr(self, 'settings'):
                self.settings = {}
            self.settings[key] = str(value)
            
            logger.debug(f"Saved setting: {key} = {value}")
        except Exception as e:
            logger.error(f"Failed to save setting {key}: {e}", exc_info=True)
    
    async def _init_ui(self) -> None:
        """Initialize the user interface."""
        logger.info("Initializing UI...")
        
        # Create and show main window
        self._main_window = MainWindow(self)
        
        # Apply saved window state
        if "window/geometry" in self.settings:
            self._main_window.restoreGeometry(bytes.fromhex(self.settings["window/geometry"]))
        if "window/state" in self.settings:
            self._main_window.restoreState(bytes.fromhex(self.settings["window/state"]))
        
        self._main_window.show()
        logger.info("UI initialized")
    
    async def _init_background_services(self) -> None:
        """Initialize background services."""
        logger.info("Initializing background services...")
        # Initialize background services here
        logger.info("Background services initialized")
        
    def setup_styles(self) -> None:
        """Set up application-wide styles."""
        self._qt_app.setStyle("Fusion")
        
        # Set application font
        font = QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        self._qt_app.setFont(font)
        
        # Set up palette
        palette = self._qt_app.palette()
        
        # Base colors
        base_color = QColor("#f0f0f0")
        text_color = QColor("#333333")
        highlight_color = QColor("#0078d7")
        
        # Set palette colors
        palette.setColor(QPalette.ColorRole.Window, base_color)
        palette.setColor(QPalette.ColorRole.WindowText, text_color)
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.AlternateBase, base_color)
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ToolTipText, text_color)
        palette.setColor(QPalette.ColorRole.Text, text_color)
        palette.setColor(QPalette.ColorRole.Button, base_color)
        palette.setColor(QPalette.ColorRole.ButtonText, text_color)
        palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Link, highlight_color)
        palette.setColor(QPalette.ColorRole.Highlight, highlight_color)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        
        self._qt_app.setPalette(palette)
        
        # Set style sheet for consistent look across platforms
        style_sheet = """
            QToolTip {
                border: 1px solid #76797c;
                background-color: #f0f0f0;
                color: #333333;
                padding: 5px;
                opacity: 225;
            }
            
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #f6f7fa, stop:1 #e6e7e9);
                min-width: 80px;
            }
            
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #e6e7e9, stop:1 #d6d7d9);
            }
            
            QPushButton:pressed {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #d6d7d9, stop:1 #c6c7c9);
            }
            
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, 
            QDoubleSpinBox, QDateEdit, QDateTimeEdit, QTimeEdit {
                padding: 3px 5px;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background: #ffffff;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
            }
            
            QTabBar::tab {
                padding: 5px 10px;
                margin-right: 2px;
                background: #e0e0e0;
                border: 1px solid #d0d0d0;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #f0f0f0;
            }
            
            QStatusBar {
                border-top: 1px solid #d0d0d0;
                background: #e0e0e0;
            }
        """
        self._qt_app.setStyleSheet(style_sheet)


def run_application() -> int:
    """Run the Phoenix application."""
    # Set up signal handlers for clean shutdown
    def signal_handler(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        if 'app' in globals():
            asyncio.create_task(app.shutdown())
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create the application
    app = PhoenixApplication(sys.argv)
    
    # Run the application
    try:
        return asyncio.get_event_loop().run_until_complete(app.run())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        asyncio.get_event_loop().run_until_complete(app.shutdown())
        return 0
    except Exception as e:
        logger.critical("Unhandled exception: %s", str(e), exc_info=True)
        return 1
    finally:
        # Clean up asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.stop()
        if not loop.is_closed():
            loop.close()
