"""
Action suggestions panel for emails.

This module provides a widget that displays AI-suggested actions for an email.
"""
from typing import List, Dict, Any, Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QSizePolicy, QMenu, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor

from ...models.email_management import Email, EmailAction
from ...ai.email_processor import get_email_processor

class ActionButton(QToolButton):
    """A button representing an action that can be taken on an email."""
    
    def __init__(self, action: EmailAction, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.action = action
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the button UI."""
        self.setText(self.action.name)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(32)
        
        # Set icon if available
        if self.action.icon:
            self.setIcon(QIcon.fromTheme(self.action.icon))
        
        # Add dropdown arrow for actions with parameters
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        
        # Create menu for additional options
        self.menu = QMenu(self)
        self.setMenu(self.menu)
        
        # Add default action (executed on button click)
        default_action = QAction(f"{self.action.name}", self)
        default_action.triggered.connect(self._on_default_action)
        self.setDefaultAction(default_action)
    
    def _on_default_action(self) -> None:
        """Handle the default action."""
        self.clicked.emit()


class ActionSuggestionPanel(QFrame):
    """Panel showing suggested actions for an email."""
    
    # Signals
    action_triggered = pyqtSignal(str, dict)  # action_name, parameters
    
    def __init__(self, db_session, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_session
        self.email: Optional[Email] = None
        self.suggested_actions: List[Dict[str, Any]] = []
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the UI."""
        self.setObjectName("actionSuggestionPanel")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("Suggested Actions")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)
        
        # Actions container
        self.actions_layout = QVBoxLayout()
        self.actions_layout.setSpacing(4)
        layout.addLayout(self.actions_layout)
        
        # No suggestions label
        self.no_suggestions = QLabel("No suggestions available")
        self.no_suggestions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_suggestions.setStyleSheet("color: gray;")
        self.actions_layout.addWidget(self.no_suggestions)
        
        # Add some styling
        self.setStyleSheet("""
            #actionSuggestionPanel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
            }
            QToolButton {
                text-align: left;
                padding: 4px 8px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QToolButton:hover {
                background-color: #e9ecef;
            }
            QToolButton::menu-button {
                border: none;
                width: 20px;
            }
        """)
    
    def set_email(self, email: Optional[Email]) -> None:
        """Set the email to show actions for."""
        self.email = email
        self._clear_actions()
        
        if not email:
            self.no_suggestions.setVisible(True)
            return
        
        # Get suggested actions from AI
        self._load_suggested_actions()
    
    def _clear_actions(self) -> None:
        """Clear all action buttons."""
        while self.actions_layout.count() > 0:
            item = self.actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.no_suggestions.setVisible(False)
    
    def _load_suggested_actions(self) -> None:
        """Load suggested actions for the current email."""
        if not self.email:
            return
        
        # Get AI processor and suggest actions
        processor = get_email_processor(self.db)
        
        # This would be async in a real implementation
        # For now, we'll use a placeholder
        self.suggested_actions = [
            {'action_id': 1, 'name': 'Reply', 'confidence': 0.85, 'icon': 'mail-reply'},
            {'action_id': 2, 'name': 'Forward', 'confidence': 0.7, 'icon': 'mail-forward'},
            {'action_id': 3, 'name': 'Create Task', 'confidence': 0.6, 'icon': 'task'},
            {'action_id': 4, 'name': 'Schedule Meeting', 'confidence': 0.5, 'icon': 'appointment-new'},
        ]
        
        self._display_actions()
    
    def _display_actions(self) -> None:
        """Display the suggested actions."""
        if not self.suggested_actions:
            self.no_suggestions.setVisible(True)
            return
        
        self.no_suggestions.setVisible(False)
        
        # Sort actions by confidence (highest first)
        sorted_actions = sorted(
            self.suggested_actions,
            key=lambda x: x.get('confidence', 0),
            reverse=True
        )
        
        # Add action buttons
        for action_data in sorted_actions:
            action = EmailAction(
                id=action_data['action_id'],
                name=action_data['name'],
                icon=action_data.get('icon')
            )
            
            btn = ActionButton(action, self)
            btn.clicked.connect(
                lambda checked, a=action_data: self._on_action_triggered(a['name'], {})
            )
            
            # Add confidence indicator
            confidence = action_data.get('confidence', 0)
            if confidence > 0:
                btn.setToolTip(f"Confidence: {confidence*100:.0f}%")
            
            self.actions_layout.addWidget(btn)
    
    def _on_action_triggered(self, action_name: str, parameters: Dict[str, Any]) -> None:
        """Handle action button click."""
        self.action_triggered.emit(action_name, parameters)
        
        # Log the action for learning
        if self.email:
            self._log_action(action_name, parameters)
    
    def _log_action(self, action_name: str, parameters: Dict[str, Any]) -> None:
        """Log the action for learning purposes."""
        # In a real implementation, this would save to the database
        # and update the AI model
        print(f"Action taken: {action_name} with params {parameters}")
        
        # Example of how we might log this to the database:
        """
        action = EmailActionTaken(
            email_id=self.email.id,
            action_name=action_name,
            parameters=parameters,
            timestamp=datetime.utcnow()
        )
        self.db.add(action)
        self.db.commit()
        """


class EmailActionPanel(QWidget):
    """Container for action buttons in the email view."""
    
    def __init__(self, db_session, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_session
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Action buttons (standard email actions)
        self.action_buttons = QHBoxLayout()
        self.action_buttons.setSpacing(4)
        
        # Standard email action buttons
        self.reply_btn = self._create_action_button("Reply", "mail-reply")
        self.reply_all_btn = self._create_action_button("Reply All", "mail-reply-all")
        self.forward_btn = self._create_action_button("Forward", "mail-forward")
        
        # Add buttons to layout
        self.action_buttons.addWidget(self.reply_btn)
        self.action_buttons.addWidget(self.reply_all_btn)
        self.action_buttons.addWidget(self.forward_btn)
        self.action_buttons.addStretch()
        
        layout.addLayout(self.action_buttons)
        
        # Suggested actions panel
        self.suggestions_panel = ActionSuggestionPanel(self.db, self)
        self.suggestions_panel.action_triggered.connect(self._on_action_triggered)
        layout.addWidget(self.suggestions_panel)
    
    def _create_action_button(self, text: str, icon_name: str) -> QPushButton:
        """Create a standard action button."""
        btn = QPushButton(text, self)
        btn.setIcon(QIcon.fromTheme(icon_name))
        btn.setIconSize(QSize(16, 16))
        return btn
    
    def set_email(self, email: Optional[Email]) -> None:
        """Set the email to show actions for."""
        self.suggestions_panel.set_email(email)
    
    def _on_action_triggered(self, action_name: str, parameters: Dict[str, Any]) -> None:
        """Handle action triggered from suggestions."""
        # In a real implementation, this would trigger the appropriate action
        print(f"Action triggered: {action_name} with params {parameters}")
