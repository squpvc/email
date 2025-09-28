"""
Email view widget for displaying email content.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QDesktopServices, QTextDocument, QTextCursor, QTextCharFormat, QTextFormat, QTextCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
    QTextBrowser, QScrollArea, QFrame, QMenu, QSizePolicy
)

from ...models import Email, EmailStatus


class EmailView(QScrollArea):
    """Widget for displaying email content."""
    
    def __init__(self, parent=None):
        """Initialize the email view."""
        super().__init__(parent)
        self._current_email = None
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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        self.subject_label = QLabel()
        self.subject_label.setWordWrap(True)
        self.subject_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 8px;
        """)
        layout.addWidget(self.subject_label)
        
        # Sender info
        self.sender_label = QLabel()
        self.sender_label.setStyleSheet("""
            font-size: 14px;
            color: #333;
            margin-bottom: 4px;
        """)
        layout.addWidget(self.sender_label)
        
        # Date and actions
        header_bottom = QHBoxLayout()
        header_bottom.setContentsMargins(0, 0, 0, 0)
        header_bottom.setSpacing(12)
        
        self.date_label = QLabel()
        self.date_label.setStyleSheet("color: #666; font-size: 12px;")
        
        # Action buttons
        button_style = """
            QToolButton {
                border: none;
                background: transparent;
                padding: 4px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background: #f0f0f0;
            }
        """
        
        from PyQt6.QtWidgets import QStyle
        
        self.reply_btn = QToolButton()
        self.reply_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.reply_btn.setToolTip("Reply")
        self.reply_btn.setStyleSheet(button_style)
        
        self.reply_all_btn = QToolButton()
        self.reply_all_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.reply_all_btn.setToolTip("Reply All")
        self.reply_all_btn.setStyleSheet(button_style)
        
        self.forward_btn = QToolButton()
        self.forward_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.forward_btn.setToolTip("Forward")
        self.forward_btn.setStyleSheet(button_style)
        
        self.more_btn = QToolButton()
        self.more_btn.setText("⋮")
        self.more_btn.setToolTip("More actions")
        self.more_btn.setStyleSheet(button_style)
        
        header_bottom.addWidget(self.date_label)
        header_bottom.addStretch()
        header_bottom.addWidget(self.reply_btn)
        header_bottom.addWidget(self.reply_all_btn)
        header_bottom.addWidget(self.forward_btn)
        header_bottom.addWidget(self.more_btn)
        
        layout.addLayout(header_bottom)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(separator)
        
        # Recipients (To, Cc, Bcc)
        self.recipients_widget = QWidget()
        recipients_layout = QVBoxLayout(self.recipients_widget)
        recipients_layout.setContentsMargins(0, 0, 0, 0)
        recipients_layout.setSpacing(4)
        
        self.to_label = QLabel()
        self.to_label.setStyleSheet("color: #666; font-size: 13px;")
        recipients_layout.addWidget(self.to_label)
        
        self.cc_label = QLabel()
        self.cc_label.setStyleSheet("color: #666; font-size: 13px;")
        self.cc_label.hide()
        recipients_layout.addWidget(self.cc_label)
        
        self.bcc_label = QLabel()
        self.bcc_label.setStyleSheet("color: #666; font-size: 13px;")
        self.bcc_label.hide()
        recipients_layout.addWidget(self.bcc_label)
        
        layout.addWidget(self.recipients_widget)
        
        # Email body
        self.email_content = QTextBrowser()
        self.email_content.setOpenExternalLinks(True)
        self.email_content.setOpenLinks(True)
        self.email_content.setReadOnly(True)
        self.email_content.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                border: none;
                font-family: Arial, sans-serif;
                font-size: 14px;
                color: #333;
                line-height: 1.5;
            }
            a {
                color: #1a73e8;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            blockquote {
                border-left: 2px solid #ddd;
                margin: 5px 0;
                padding-left: 10px;
                color: #666;
            }
        """)
        
        layout.addWidget(self.email_content, 1)
        
        # Attachments
        self.attachments_widget = QWidget()
        self.attachments_layout = QVBoxLayout(self.attachments_widget)
        self.attachments_layout.setContentsMargins(0, 0, 0, 0)
        self.attachments_layout.setSpacing(4)
        
        attachments_label = QLabel("Attachments:")
        attachments_label.setStyleSheet("font-weight: bold; color: #666;")
        self.attachments_layout.addWidget(attachments_label)
        
        self.attachments_container = QWidget()
        self.attachments_container_layout = QVBoxLayout(self.attachments_container)
        self.attachments_container_layout.setContentsMargins(0, 0, 0, 0)
        self.attachments_container_layout.setSpacing(4)
        
        self.attachments_layout.addWidget(self.attachments_container)
        self.attachments_widget.hide()
        
        layout.addWidget(self.attachments_widget)
        
        # Set initial empty state
        self.clear()
    
    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self.reply_btn.clicked.connect(self._on_reply)
        self.reply_all_btn.clicked.connect(self._on_reply_all)
        self.forward_btn.clicked.connect(self._on_forward)
        self.more_btn.clicked.connect(self._show_more_actions)
    
    def set_email(self, email_data: Dict[str, Any]) -> None:
        """Set the email to display."""
        self._current_email = email_data
        
        # Update UI with email data
        self.subject_label.setText(email_data.get("subject", "(No subject)"))
        self.sender_label.setText(
            f"From: {email_data.get('sender_name', email_data.get('sender_email', 'Unknown'))}"
        )
        
        # Format date
        date = email_data.get("date")
        if isinstance(date, str):
            # Parse date string if needed
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                date = None
        
        if date:
            if isinstance(date, datetime):
                self.date_label.setText(date.strftime("%A, %B %d, %Y at %I:%M %p"))
            else:
                self.date_label.setText(str(date))
        
        # Set recipients
        self._set_recipients("To", email_data.get("to", []))
        
        cc = email_data.get("cc", [])
        if cc:
            self._set_recipients("Cc", cc, self.cc_label)
        
        bcc = email_data.get("bcc", [])
        if bcc:
            self._set_recipients("Bcc", bcc, self.bcc_label)
        
        # Set email body
        self._set_email_body(
            email_data.get("body_html"),
            email_data.get("body_text", "")
        )
        
        # Set attachments
        attachments = email_data.get("attachments", [])
        if attachments:
            self._set_attachments(attachments)
        else:
            self.attachments_widget.hide()
        
        # Show the content
        self.show()
    
    def _set_recipients(self, label: str, recipients: List[Dict[str, str]], 
                       label_widget: QLabel = None) -> None:
        """Set the recipients for a given type (To, Cc, Bcc)."""
        if not label_widget:
            label_widget = self.to_label
        
        if not recipients:
            label_widget.hide()
            return
        
        recipient_text = f"{label}: "
        recipient_text += ", ".join(
            f"{r.get('name', r.get('email', ''))} <{r.get('email', '')}>"
            for r in recipients
        )
        
        label_widget.setText(recipient_text)
        label_widget.show()
    
    def _set_email_body(self, html: str = None, plain_text: str = "") -> None:
        """Set the email body content."""
        if html:
            # Use HTML content if available
            self.email_content.setHtml(html)
        else:
            # Otherwise use plain text with basic formatting
            document = QTextDocument()
            cursor = QTextCursor(document)
            
            # Set default font
            font = document.defaultFont()
            font.setPointSize(10)
            document.setDefaultFont(font)
            
            # Convert plain text to HTML with basic formatting
            text = plain_text.replace("\n", "<br>")
            
            # Handle quotes (common in email replies)
            text = text.replace("&gt; ", "<span style='color:#666;'>&gt; </span>")
            
            # Handle links
            # This is a simple regex-like approach, for production use a proper URL detector
            import re
            text = re.sub(
                r'(https?://\S+)',
                r'<a href="\1">\1</a>',
                text
            )
            
            cursor.insertHtml(f"<div>{text}</div>")
            self.email_content.setDocument(document)
    
    def _set_attachments(self, attachments: List[Dict[str, str]]) -> None:
        """Set the email attachments."""
        # Clear existing attachments
        while self.attachments_container_layout.count():
            item = self.attachments_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new attachments
        for attachment in attachments:
            self._add_attachment(attachment)
        
        self.attachments_widget.show()
    
    def _add_attachment(self, attachment: Dict[str, str]) -> None:
        """Add a single attachment to the view."""
        filename = attachment.get("filename", "unnamed")
        size = self._format_size(attachment.get("size", 0))
        
        attachment_widget = QToolButton()
        attachment_widget.setText(f"📎 {filename} ({size})")
        attachment_widget.setToolTip(f"Click to open: {filename}")
        attachment_widget.setStyleSheet("""
            QToolButton {
                text-align: left;
                padding: 4px 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: #f9f9f9;
                color: #1a73e8;
            }
            QToolButton:hover {
                background: #f0f0f0;
                text-decoration: underline;
            }
        """)
        
        # Store the URL or path to open when clicked
        attachment_widget.clicked.connect(
            lambda _, url=attachment.get("url", ""): self._open_attachment(url)
        )
        
        self.attachments_container_layout.addWidget(attachment_widget)
    
    def _open_attachment(self, url: str) -> None:
        """Open an attachment with the default application."""
        if not url:
            return
            
        # In a real app, you'd want to handle this more securely
        QDesktopServices.openUrl(QUrl.fromLocalFile(url))
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in a human-readable format."""
        if not size_bytes:
            return "0 B"
            
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def clear(self) -> None:
        """Clear the email view."""
        self._current_email = None
        self.subject_label.clear()
        self.sender_label.clear()
        self.date_label.clear()
        self.to_label.clear()
        self.cc_label.clear()
        self.bcc_label.clear()
        self.email_content.clear()
        self.attachments_widget.hide()
        
        # Clear attachments
        while self.attachments_container_layout.count():
            item = self.attachments_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _on_reply(self) -> None:
        """Handle reply button click."""
        if not self._current_email:
            return
        
        # TODO: Implement reply functionality
        print(f"Replying to: {self._current_email.get('subject')}")
    
    def _on_reply_all(self) -> None:
        """Handle reply all button click."""
        if not self._current_email:
            return
        
        # TODO: Implement reply all functionality
        print(f"Replying all to: {self._current_email.get('subject')}")
    
    def _on_forward(self) -> None:
        """Handle forward button click."""
        if not self._current_email:
            return
        
        # TODO: Implement forward functionality
        print(f"Forwarding: {self._current_email.get('subject')}")
    
    def _show_more_actions(self) -> None:
        """Show more actions menu."""
        if not self._current_email:
            return
        
        menu = QMenu(self)
        
        mark_as_unread = menu.addAction("Mark as Unread")
        mark_as_important = menu.addAction("Mark as Important")
        menu.addSeparator()
        print_action = menu.addAction("Print...")
        menu.addSeparator()
        report_phishing = menu.addAction("Report Phishing")
        report_spam = menu.addAction("Report Spam")
        
        # Show the menu at the button position
        action = menu.exec(self.more_btn.mapToGlobal(
            self.more_btn.rect().bottomLeft()
        ))
        
        # Handle the selected action
        if action == mark_as_unread:
            self._mark_as_unread()
        elif action == mark_as_important:
            self._mark_as_important()
        elif action == print_action:
            self._print_email()
        elif action == report_phishing:
            self._report_phishing()
        elif action == report_spam:
            self._report_spam()
    
    def _mark_as_unread(self) -> None:
        """Mark the current email as unread."""
        if self._current_email:
            self._current_email["status"] = EmailStatus.UNREAD
            # TODO: Update the email status in the database
            print(f"Marked as unread: {self._current_email.get('subject')}")
    
    def _mark_as_important(self) -> None:
        """Mark the current email as important."""
        if self._current_email:
            # TODO: Implement mark as important
            print(f"Marked as important: {self._current_email.get('subject')}")
    
    def _print_email(self) -> None:
        """Print the current email."""
        if self._current_email:
            # TODO: Implement print functionality
            print(f"Printing: {self._current_email.get('subject')}")
    
    def _report_phishing(self) -> None:
        """Report the current email as phishing."""
        if self._current_email:
            # TODO: Implement report phishing
            print(f"Reported as phishing: {self._current_email.get('subject')}")
    
    def _report_spam(self) -> None:
        """Report the current email as spam."""
        if self._current_email:
            # TODO: Implement report spam
            print(f"Reported as spam: {self._current_email.get('subject')}")
