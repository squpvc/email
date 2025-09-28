"""
Email list widget for displaying a list of emails.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QSortFilterProxyModel, QModelIndex
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListView, QAbstractItemView, QMenu, QStyle,
    QToolButton, QHBoxLayout, QLabel, QFrame, QStyledItemDelegate, QLineEdit, QStatusBar
)

from ...models import Email, EmailStatus


class EmailItemDelegate(QStyledItemDelegate):
    """Custom delegate for rendering email list items."""
    
    def __init__(self, parent=None):
        """Initialize the delegate."""
        super().__init__(parent)
        self._unread_color = QColor(0, 102, 204)  # Blue for unread
        self._read_color = QColor(51, 51, 51)     # Dark gray for read
        self._selected_color = QColor(255, 255, 255)  # White for selected text
    
    def paint(self, painter, option, index):
        """Paint the email list item."""
        # Get the email data
        email = index.data(Qt.ItemDataRole.UserRole)
        if not email:
            return super().paint(painter, option, index)
        
        # Set up the painter
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        
        # Get email status with a default of RECEIVED if not present
        status = email.get('status', EmailStatus.RECEIVED)
        
        # Draw background and set text color
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            text_color = self._selected_color
        else:
            text_color = self._unread_color if status == EmailStatus.RECEIVED else self._read_color
        
        # Set up text metrics and fonts
        font = painter.font()
        bold_font = font
        bold_font.setBold(status == EmailStatus.RECEIVED)
        
        # Calculate text positions
        padding = 8
        line_spacing = 4
        y = option.rect.y() + padding
        x = option.rect.x() + padding
        width = option.rect.width() - 2 * padding
        
        # Draw sender
        painter.setFont(bold_font)
        painter.setPen(text_color)
        sender_text = email.get('sender_name') or email.get('sender_email', '')
        sender_rect = painter.boundingRect(
            x, y, width, 0, 
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            sender_text
        )
        painter.drawText(sender_rect, Qt.AlignmentFlag.AlignLeft, sender_text)
        
        # Draw subject
        y += sender_rect.height() + line_spacing
        subject = email.get('subject', '(No subject)')
        subject_rect = painter.boundingRect(
            x, y, width, 0,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            subject
        )
        painter.drawText(subject_rect, Qt.AlignmentFlag.AlignLeft, subject)
        
        # Draw preview and date
        y += subject_rect.height() + line_spacing
        preview_font = font
        preview_font.setPointSize(font.pointSize() - 1)
        painter.setFont(preview_font)
        
        # Calculate available width for preview (leave space for date)
        date_text = self._format_date(email.get('date', datetime.now()))
        date_rect = painter.boundingRect(
            0, 0, 200, 0,  # Large width to get full text size
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignRight,
            date_text
        )
        
        preview_width = width - date_rect.width() - 10  # 10px spacing
        
        # Draw preview
        preview_text = email.get('preview', '')
        painter.setPen(QColor(102, 102, 102))  # Gray for preview
        painter.drawText(
            x, y, preview_width, option.rect.height() - y - padding,
            Qt.TextFlag.TextWordWrap,
            preview_text[:100] + ("..." if len(preview_text) > 100 else "")
        )
        
        # Draw date
        painter.setPen(QColor(136, 136, 136))  # Lighter gray for date
        painter.drawText(
            x + preview_width + 10, y, 
            date_rect.width(), option.rect.height() - y - padding,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            date_text
        )
        
        # Draw bottom border
        painter.setPen(QColor(238, 238, 238))  # Light gray border
        painter.drawLine(
            x, option.rect.bottom() - 1,
            option.rect.right() - padding, option.rect.bottom() - 1
        )
        
        painter.restore()
    
    def sizeHint(self, option, index):
        """Return the size hint for the item."""
        # Fixed height for each email item
        return QSize(200, 100)  # Width is flexible, height is fixed
    
    def _format_date(self, date: datetime) -> str:
        """Format the date for display."""
        if not date:
            return ""
            
        now = datetime.now()
        delta = now - date
        
        if delta.days == 0:
            # Today - show time
            return date.strftime("%I:%M %p").lstrip('0')
        elif delta.days == 1:
            # Yesterday
            return "Yesterday"
        elif delta.days < 7:
            # This week - show day name
            return date.strftime("%A")
        elif date.year == now.year:
            # This year - show month and day
            return date.strftime("%b %d")
        else:
            # Older - show full date
            return date.strftime("%b %d, %Y")


class EmailList(QWidget):
    """Widget for displaying a list of emails."""
    
    # Signals
    email_selected = pyqtSignal(object)  # Emitted when an email is selected
    
    # Define signals
    compose_requested = pyqtSignal()
    reply_requested = pyqtSignal(dict, bool)  # email_data, reply_all
    forward_requested = pyqtSignal(dict)      # email_data
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the email list."""
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
        
        # Store the currently selected email
        self._selected_email = None
        
        # Load sample data (for testing)
        self._load_sample_data()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(4)
        
        # Add toolbar buttons
        self.refresh_btn = QToolButton()
        self.refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_btn.setToolTip("Refresh")
        
        self.compose_btn = QToolButton()
        self.compose_btn.setIcon(QIcon.fromTheme("mail-message-new"))
        self.compose_btn.setToolTip("New Email")
        
        self.archive_btn = QToolButton()
        self.archive_btn.setIcon(QIcon.fromTheme("mail-archive"))
        self.archive_btn.setToolTip("Archive")
        
        self.trash_btn = QToolButton()
        self.trash_btn.setIcon(QIcon.fromTheme("user-trash"))
        self.trash_btn.setToolTip("Move to Trash")
        
        self.spam_btn = QToolButton()
        self.spam_btn.setIcon(QIcon.fromTheme("mail-mark-junk"))
        self.spam_btn.setToolTip("Mark as Spam")
        
        # Add buttons to toolbar
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.compose_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.archive_btn)
        toolbar_layout.addWidget(self.trash_btn)
        toolbar_layout.addWidget(self.spam_btn)
        
        # Add search bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search emails...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(300)
        toolbar_layout.addWidget(self.search_edit)
        
        layout.addWidget(toolbar)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Create list view
        self.list_view = QListView()
        self.list_view.setItemDelegate(EmailItemDelegate(self))
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Create model
        self.model = QStandardItemModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.list_view.setModel(self.proxy_model)
        
        layout.addWidget(self.list_view)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_label = QLabel("No emails")
        self.status_bar.addWidget(self.status_label)
        layout.addWidget(self.status_bar)
    
    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self.list_view.clicked.connect(self._on_item_clicked)
        self.list_view.doubleClicked.connect(self._on_item_double_clicked)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)
        
        # Connect toolbar buttons
        self.refresh_btn.clicked.connect(self.refresh)
        self.compose_btn.clicked.connect(self.compose_email)
        self.archive_btn.clicked.connect(self.archive_selected)
        self.trash_btn.clicked.connect(self.trash_selected)
        self.spam_btn.clicked.connect(self.mark_as_spam)
        
        # Connect search
        self.search_edit.textChanged.connect(self._on_search_text_changed)
    
    def _load_sample_data(self) -> None:
        """Load sample email data (for testing)."""
        # This would be replaced with actual data loading
        from datetime import datetime, timedelta
        
        sample_emails = [
            {
                "id": "1",
                "subject": "Welcome to Project Phoenix",
                "sender_name": "Phoenix Team",
                "sender_email": "noreply@phoenix.example.com",
                "date": datetime.now() - timedelta(hours=2),
                "preview": "Thank you for installing Project Phoenix. We're excited to have you on board!",
                "status": EmailStatus.RECEIVED,
                "labels": ["inbox", "important"]
            },
            {
                "id": "2",
                "subject": "Your weekly digest",
                "sender_name": "GitHub",
                "sender_email": "notifications@github.com",
                "date": datetime.now() - timedelta(days=1),
                "preview": "Here's what's been happening in your repositories this week...",
                "status": EmailStatus.RECEIVED,
                "labels": ["inbox", "updates"]
            },
            {
                "id": "3",
                "subject": "Invoice #12345",
                "sender_name": "Stripe",
                "sender_email": "receipts@stripe.com",
                "date": datetime.now() - timedelta(days=3),
                "preview": "Your invoice for $9.99 has been paid. Thank you for your business!",
                "status": EmailStatus.RECEIVED,
                "labels": ["inbox", "receipts"]
            },
            {
                "id": "4",
                "subject": "Your order has shipped",
                "sender_name": "Amazon",
                "sender_email": "shipment-update@amazon.com",
                "date": datetime.now() - timedelta(days=5),
                "preview": "Your order #D01-1234567-8901234 has shipped and is on its way to you.",
                "status": EmailStatus.RECEIVED,
                "labels": ["inbox", "shipping"]
            },
            {
                "id": "5",
                "subject": "Security alert: New login detected",
                "sender_name": "Google Accounts",
                "sender_email": "no-reply@accounts.google.com",
                "date": datetime.now() - timedelta(weeks=2),
                "preview": "New sign-in from Chrome on Windows. If this was you, you can ignore this message.",
                "status": EmailStatus.RECEIVED,
                "labels": ["inbox", "alerts"]
            }
        ]
        
        self.set_emails(sample_emails)
    
    def set_emails(self, emails: List[Dict[str, Any]]) -> None:
        """Set the list of emails to display."""
        self.model.clear()
        
        for email_data in emails:
            item = QStandardItem()
            item.setData(email_data, Qt.ItemDataRole.UserRole)
            self.model.appendRow(item)
        
        # Update status
        self._update_status()
    
    def refresh(self) -> None:
        """Refresh the email list."""
        self.refresh_requested.emit()
        self._update_status()
    
    def compose_email(self) -> None:
        """Emit signal to compose a new email."""
        self.compose_requested.emit()
    
    def archive_selected(self) -> None:
        """Archive the selected email(s)."""
        # TODO: Implement archive
        print("Archiving selected emails...")
    
    def trash_selected(self) -> None:
        """Move the selected email(s) to trash."""
        # TODO: Implement move to trash
        print("Moving to trash...")
    
    def mark_as_spam(self) -> None:
        """Mark the selected email(s) as spam."""
        # TODO: Implement mark as spam
        print("Marking as spam...")
    
    def _on_item_clicked(self, index: QModelIndex) -> None:
        """Handle item click."""
        if not index.isValid():
            return
            
        # Get the email data
        source_index = self.proxy_model.mapToSource(index)
        self._selected_email = self.model.itemFromIndex(source_index).data(Qt.ItemDataRole.UserRole)
        
        # Mark as read if the email is in RECEIVED status
        if self._selected_email.get("status") == EmailStatus.RECEIVED:
            # We don't change the status from RECEIVED since that's our only "unread" state
            # Instead, we can add a 'read' flag to the email data if needed
            self._selected_email["read"] = True
            self.model.setData(source_index, self._selected_email, Qt.ItemDataRole.UserRole)
        
        # Emit signal
        self.email_selected.emit(self._selected_email)
    
    def _on_item_double_clicked(self, index: QModelIndex) -> None:
        """Handle item double click."""
        if not index.isValid():
            return
            
        # Get the email data
        source_index = self.proxy_model.mapToSource(index)
        email_data = self.model.itemFromIndex(source_index).data(Qt.ItemDataRole.UserRole)
        
        # TODO: Open email in a new window or tab
        print(f"Opening email: {email_data.get('subject')}")
    
    def _show_context_menu(self, position) -> None:
        """Show the context menu."""
        index = self.list_view.indexAt(position)
        if not index.isValid():
            return
            
        menu = QMenu()
        
        # Add actions
        reply_action = menu.addAction("Reply")
        reply_all_action = menu.addAction("Reply All")
        forward_action = menu.addAction("Forward")
        menu.addSeparator()
        archive_action = menu.addAction("Archive")
        trash_action = menu.addAction("Move to Trash")
        spam_action = menu.addAction("Mark as Spam")
        
        # Execute the menu
        action = menu.exec(self.list_view.viewport().mapToGlobal(position))
        
        # Handle actions
        if action == reply_action:
            self._reply_email()
        elif action == reply_all_action:
            self._reply_all_email()
        elif action == forward_action:
            self._forward_email()
        elif action == archive_action:
            self.archive_selected()
        elif action == trash_action:
            self.trash_selected()
        elif action == spam_action:
            self.mark_as_spam()
    
    def _reply_email(self) -> None:
        """Emit signal to reply to the selected email."""
        if not self._selected_email:
            return
        self.reply_requested.emit(self._selected_email, False)
    
    def _reply_all_email(self) -> None:
        """Emit signal to reply all to the selected email."""
        if not self._selected_email:
            return
        self.reply_requested.emit(self._selected_email, True)
    
    def _forward_email(self) -> None:
        """Emit signal to forward the selected email."""
        if not self._selected_email:
            return
        self.forward_requested.emit(self._selected_email)
    
    def _on_search_text_changed(self, text: str) -> None:
        """Handle search text changes."""
        self.proxy_model.setFilterFixedString(text)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._update_status()
    
    def _update_status(self) -> None:
        """Update the status bar."""
        total = self.proxy_model.rowCount()
        if total == 0:
            self.status_label.setText("No emails")
        elif total == 1:
            self.status_label.setText("1 email")
        else:
            self.status_label.setText(f"{total} emails")
