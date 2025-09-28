"""
Search results dialog for displaying AI search results.
"""
from typing import List, Dict, Any

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QLabel,
    QDialogButtonBox, QAbstractItemView, QHBoxLayout, QTextEdit
)
from PyQt6.QtGui import QFont, QTextCursor

class SearchResultItem(QListWidgetItem):
    """Custom list item for search results."""
    
    def __init__(self, result: Dict[str, Any], parent=None):
        """Initialize the search result item.
        
        Args:
            result: The search result data
            parent: Parent widget
        """
        super().__init__(parent)
        self.result = result
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the item UI."""
        # Create a widget to hold the item content
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Subject
        subject = QLabel(self.result.get('subject', 'No subject'))
        subject_font = QFont()
        subject_font.setBold(True)
        subject.setFont(subject_font)
        
        # Sender and date
        metadata = QLabel(
            f"From: {self.result.get('from', 'Unknown')} • "
            f"Date: {self.result.get('date', 'Unknown')}"
        )
        metadata.setStyleSheet("color: gray;")
        
        # Snippet (first 100 chars of content)
        content = self.result.get('content', '')
        snippet = content[:100] + ('...' if len(content) > 100 else '')
        snippet_label = QLabel(snippet)
        snippet_label.setWordWrap(True)
        
        layout.addWidget(subject)
        layout.addWidget(metadata)
        layout.addWidget(snippet_label)
        
        # Set the widget as the list item's widget
        self.setSizeHint(widget.sizeHint())
        
        # Store the full content for the preview
        self.full_content = content

class SearchResultsDialog(QDialog):
    """Dialog for displaying search results."""
    
    # Signal emitted when an email is selected
    email_selected = pyqtSignal(str)  # email_id
    
    def __init__(self, 
                parent=None, 
                results: List[Dict[str, Any]] = None,
                title: str = "Search Results"):
        """Initialize the search results dialog.
        
        Args:
            parent: Parent widget
            results: List of search results
            title: Dialog title
        """
        super().__init__(parent)
        self.results = results or []
        self.setWindowTitle(title)
        self.setMinimumSize(700, 500)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        
        # Left panel: List of results
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Right panel: Preview
        preview_panel = QVBoxLayout()
        
        self.preview_title = QLabel("Select an email to preview")
        self.preview_title.setWordWrap(True)
        self.preview_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.preview_meta = QLabel()
        self.preview_meta.setStyleSheet("color: gray;")
        
        self.preview_content = QTextEdit()
        self.preview_content.setReadOnly(True)
        self.preview_content.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background-color: #f9f9f9;
            }
        """)
        
        preview_panel.addWidget(self.preview_title)
        preview_panel.addWidget(self.preview_meta)
        preview_panel.addWidget(self.preview_content)
        
        # Add stretch to push content to the top
        preview_panel.addStretch()
        
        # Add list and preview to main layout
        layout.addWidget(self.results_list, 1)
        layout.addLayout(preview_panel, 2)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(buttons)
        
        self.setLayout(main_layout)
        
        # Populate the results list
        self._populate_results()
    
    def _populate_results(self) -> None:
        """Populate the results list with search results."""
        self.results_list.clear()
        
        for result in self.results:
            item = SearchResultItem(result)
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, item.widget)
        
        # Select the first item if available
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)
    
    def _on_selection_changed(self) -> None:
        """Handle selection change in the results list."""
        current_item = self.results_list.currentItem()
        if not current_item:
            return
            
        # Update preview with selected item's content
        result = current_item.result
        self.preview_title.setText(result.get('subject', 'No subject'))
        
        # Format metadata
        meta_parts = []
        if 'from' in result:
            meta_parts.append(f"From: {result['from']}")
        if 'to' in result:
            meta_parts.append(f"To: {result['to']}")
        if 'date' in result:
            meta_parts.append(f"Date: {result['date']}")
            
        self.preview_meta.setText(" • ".join(meta_parts))
        
        # Set content with basic formatting
        self.preview_content.clear()
        
        # Add email body with basic formatting
        if 'content' in result:
            # Simple formatting for email content
            content = result['content']
            
            # Preserve line breaks and add some basic formatting
            formatted_content = content.replace('\n', '<br>')
            
            # Highlight quoted text
            lines = formatted_content.split('<br>')
            for i, line in enumerate(lines):
                if line.strip().startswith('>'):
                    lines[i] = f'<span style="color: #666; font-style: italic;">{line}</span>'
            
            self.preview_content.setHtml('<br>'.join(lines))
            
            # Scroll to top
            self.preview_content.moveCursor(QTextCursor.MoveOperation.Start)
    
    def selected_email_id(self) -> str:
        """Get the ID of the currently selected email.
        
        Returns:
            str: The email ID, or empty string if none selected
        """
        current_item = self.results_list.currentItem()
        if current_item and 'id' in current_item.result:
            return current_item.result['id']
        return ""
