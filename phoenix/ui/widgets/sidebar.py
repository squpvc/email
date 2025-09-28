"""
Sidebar widget for the main window.
"""
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QToolButton, QLabel, 
    QSizePolicy, QScrollArea, QFrame
)

from ...models import EmailAccount, EmailFolder


class Sidebar(QScrollArea):
    """Sidebar widget for navigation."""
    
    # Signals
    folder_selected = pyqtSignal(EmailFolder)
    
    def __init__(self, parent=None):
        """Initialize the sidebar."""
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Create container widget
        container = QWidget()
        self.setWidget(container)
        
        # Main layout
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Add logo and app name
        header = QLabel("Phoenix")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            padding: 10px 5px;
            border-bottom: 1px solid #e0e0e0;
        """)
        layout.addWidget(header)
        
        # Add compose button
        self.compose_btn = QToolButton()
        self.compose_btn.setText("Compose")
        self.compose_btn.setIcon(QIcon.fromTheme("mail-message-new"))
        self.compose_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.compose_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.compose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.compose_btn)
        
        # Add spacer
        layout.addSpacing(10)
        
        # Add folders section
        folders_label = QLabel("Folders")
        folders_label.setStyleSheet("""
            font-weight: bold;
            color: #666;
            padding: 5px 0;
        """)
        layout.addWidget(folders_label)
        
        # Folders container
        self.folders_layout = QVBoxLayout()
        self.folders_layout.setContentsMargins(0, 0, 0, 0)
        self.folders_layout.setSpacing(2)
        layout.addLayout(self.folders_layout)
        
        # Add spacer to push content to the top
        layout.addStretch()
        
        # Add settings button at the bottom
        self.settings_btn = QToolButton()
        self.settings_btn.setText("Settings")
        self.settings_btn.setIcon(QIcon.fromTheme("preferences-system"))
        self.settings_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.settings_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.settings_btn)
    
    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self.compose_btn.clicked.connect(self._on_compose_clicked)
        self.settings_btn.clicked.connect(self._on_settings_clicked)
    
    def add_account(self, account: EmailAccount) -> None:
        """Add an email account to the sidebar."""
        # TODO: Implement account addition with folders
        pass
    
    def _on_compose_clicked(self) -> None:
        """Handle compose button click."""
        # TODO: Implement compose new email
        print("Compose new email")
    
    def _on_settings_clicked(self) -> None:
        """Handle settings button click.
        
        Emits a signal that the main window will connect to its _show_settings method.
        """
        window = self.window()
        if hasattr(window, '_show_settings'):
            window._show_settings()
        else:
            print("Show settings (main window does not have _show_settings method)")
