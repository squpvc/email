"""
Related emails widget.

This module provides a widget that displays emails related to the currently viewed email.
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QFrame, QSizePolicy, QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor

from ...models.email_management import Email
from ...ai.learning_service import get_learning_service
from ...ai.email_processor import get_email_processor
from ...database import DatabaseManager


class EmailItemWidget(QWidget):
    """Widget for displaying an email in the related emails list."""
    
    def __init__(self, email: Email, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.email = email
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        
        # Header row (sender and date)
        header = QHBoxLayout()
        
        # Sender
        sender = self.email.sender_name or self.email.sender_email or "Unknown Sender"
        self.sender_label = QLabel(sender)
        self.sender_label.setStyleSheet("font-weight: bold;")
        
        # Date
        date_str = self.email.received_at.strftime("%b %d, %Y %I:%M %p") if self.email.received_at else ""
        self.date_label = QLabel(date_str)
        self.date_label.setStyleSheet("color: gray;")
        
        header.addWidget(self.sender_label, 1)
        header.addWidget(self.date_label, 0, Qt.AlignmentFlag.AlignRight)
        
        # Subject
        self.subject_label = QLabel(self.email.subject or "(No subject)")
        self.subject_label.setWordWrap(True)
        
        # Snippet (first few words of the body)
        snippet = ""
        if self.email.body_plain:
            snippet = self.email.body_plain[:100] + ("..." if len(self.email.body_plain) > 100 else "")
        
        self.snippet_label = QLabel(snippet)
        self.snippet_label.setWordWrap(True)
        self.snippet_label.setStyleSheet("color: #555;")
        
        # Add to layout
        layout.addLayout(header)
        layout.addWidget(self.subject_label)
        layout.addWidget(self.snippet_label)
        
        # Styling
        self.setAutoFillBackground(True)
        self.setStyleSheet("""
            EmailItemWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background: white;
                margin: 2px;
                padding: 4px;
            }
            EmailItemWidget:hover {
                background: #f5f5f5;
                border-color: #c0c0c0;
            }
        """)


class RelatedEmailsPanel(QFrame):
    """Panel showing emails related to the currently viewed email."""
    
    # Signals
    email_selected = pyqtSignal(int)  # email_id
    
    def __init__(self, db_session: DatabaseManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_session
        self.current_email: Optional[Email] = None
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the UI."""
        self.setObjectName("relatedEmailsPanel")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        self.header = QLabel("Related Emails")
        self.header.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.header)
        
        # Loading indicator
        self.loading_label = QLabel("Finding related emails...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.hide()
        layout.addWidget(self.loading_label)
        
        # Related emails list
        self.list_widget = QListWidget()
        self.list_widget.setItemDelegate(EmailItemDelegate())
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.list_widget, 1)
        
        # Styling
        self.setStyleSheet("""
            #relatedEmailsPanel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QListWidget {
                border: none;
                background: transparent;
                outline: none;
            }
            QListWidget::item {
                border: none;
                padding: 0;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background: transparent;
            }
        """)
    
    def set_email(self, email: Optional[Email]) -> None:
        """Set the email to find related emails for."""
        self.current_email = email
        self.list_widget.clear()
        
        if not email:
            return
        
        # Show loading indicator
        self.loading_label.show()
        self.list_widget.hide()
        
        # Use a timer to prevent UI freezing
        QTimer.singleShot(100, self._find_related_emails)
    
    def _find_related_emails(self) -> None:
        """Find emails related to the current email."""
        if not self.current_email:
            return
        
        try:
            # Get related emails using the email processor
            processor = get_email_processor(self.db)
            related_emails = processor.find_related_emails(
                self.current_email,
                limit=10,
                min_similarity=0.3
            )
            
            # Update the UI on the main thread
            self._update_related_emails(related_emails)
            
        except Exception as e:
            logger.error(f"Error finding related emails: {e}")
            self.loading_label.setText("Error loading related emails.")
    
    def _update_related_emails(self, related_emails: List[Dict[str, Any]]) -> None:
        """Update the UI with the related emails."""
        self.list_widget.clear()
        
        if not related_emails:
            self.loading_label.setText("No related emails found.")
            return
        
        # Hide loading indicator and show the list
        self.loading_label.hide()
        self.list_widget.show()
        
        # Add related emails to the list
        for email_data in related_emails:
            email = email_data.get('email')
            if not email:
                continue
                
            # Create a custom widget for the email
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, email.id)
            item.setSizeHint(QSize(0, 100))  # Set a fixed height for each item
            
            # Create and set the widget
            widget = EmailItemWidget(email, self)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
    
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle clicking on a related email."""
        email_id = item.data(Qt.ItemDataRole.UserRole)
        if email_id:
            self.email_selected.emit(email_id)
    
    def _show_context_menu(self, position) -> None:
        """Show context menu for a related email."""
        item = self.list_widget.itemAt(position)
        if not item:
            return
            
        email_id = item.data(Qt.ItemDataRole.UserRole)
        if not email_id:
            return
        
        menu = QMenu(self)
        
        # View email
        view_action = menu.addAction("View Email")
        view_action.triggered.connect(lambda: self.email_selected.emit(email_id))
        
        # Open in new tab
        new_tab_action = menu.addAction("Open in New Tab")
        new_tab_action.triggered.connect(lambda: self._open_in_new_tab(email_id))
        
        # Show the menu
        menu.exec(self.list_widget.viewport().mapToGlobal(position))
    
    def _open_in_new_tab(self, email_id: int) -> None:
        """Open the email in a new tab."""
        # This would be connected to the main window's tab system
        print(f"Opening email {email_id} in new tab")


class EmailItemDelegate(QStyledItemDelegate):
    """Custom delegate for styling email items in the list."""
    
    def paint(self, painter, option, index):
        # Let the default painter handle the basic item rendering
        super().paint(painter, option, index)
        
        # Add a subtle separator between items
        if index.row() < index.model().rowCount() - 1:
            painter.save()
            painter.setPen(QColor(224, 224, 224))
            painter.drawLine(
                option.rect.bottomLeft() + QPoint(8, 0),
                option.rect.bottomRight() - QPoint(8, 0)
            )
            painter.restore()
    
    def sizeHint(self, option, index):
        # Return a fixed size hint for all items
        return QSize(200, 100)


def add_related_emails_to_email_view(email_view: QWidget, db_session: DatabaseManager) -> None:
    """
    Add a related emails panel to an email view.
    
    Args:
        email_view: The email view widget to add the panel to
        db_session: Database session
    """
    # Create a splitter to divide the email view and related emails
    splitter = QSplitter(Qt.Orientation.Vertical)
    
    # Get the current content of the email view
    content = email_view.layout().takeAt(0).widget()
    
    # Create the related emails panel
    related_emails = RelatedEmailsPanel(db_session)
    
    # Add widgets to the splitter
    splitter.addWidget(content)
    splitter.addWidget(related_emails)
    
    # Set stretch factors to give more space to the email content
    splitter.setStretchFactor(0, 3)
    splitter.setStretchFactor(1, 1)
    
    # Add the splitter to the email view
    email_view.layout().addWidget(splitter)
    
    # Connect signals (assuming the email view has a current_email_changed signal)
    if hasattr(email_view, 'current_email_changed'):
        email_view.current_email_changed.connect(related_emails.set_email)
    
    # Connect the email_selected signal to the email view's load_email method
    if hasattr(email_view, 'load_email'):
        related_emails.email_selected.connect(email_view.load_email)
