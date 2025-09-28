"""
Command palette widget for quick actions.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set

from PyQt6.QtCore import Qt, pyqtSignal, QSortFilterProxyModel, QModelIndex, QSize, QEvent, QObject
from PyQt6.QtGui import (
    QKeySequence, QStandardItemModel, QStandardItem, QAction, QIcon,
    QFontMetrics, QColor, QPalette, QKeyEvent, QShortcut
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListView, QAbstractItemView,
    QLabel, QSizePolicy, QStyledItemDelegate, QStyle,
    QApplication, QStyleOptionViewItem, QHBoxLayout
)

# Add fuzzy search functionality
from rapidfuzz import fuzz, process

@dataclass
class CommandItem:
    """Represents a command in the command palette."""
    id: str
    name: str
    handler: Callable[[], None]
    shortcut: str = ""
    icon: str = ""
    category: str = "General"
    description: str = ""
    keywords: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        # Initialize keywords with name, category, and description terms
        if not self.keywords:
            self.keywords = set()
        
        # Add basic search terms
        self.keywords.update(term.lower() for term in self.name.split())
        self.keywords.update(term.lower() for term in self.category.split())
        self.keywords.update(term.lower() for term in self.description.split())
        
        # Add shortcut without modifiers for search
        if self.shortcut:
            shortcut_terms = self.shortcut.replace('+', ' ').lower().split()
            self.keywords.update(term for term in shortcut_terms if len(term) > 1)
    
    def matches(self, search_term: str) -> bool:
        """Check if the command matches the search term using fuzzy matching."""
        if not search_term:
            return True
            
        search_terms = search_term.lower().split()
        all_keywords = ' '.join(self.keywords)
        
        # Use fuzzy matching to score the match
        for term in search_terms:
            if not term:
                continue
                
            # Check for exact matches first (faster)
            if any(term in keyword for keyword in self.keywords):
                continue
                
            # Use fuzzy matching for partial matches
            best_score = fuzz.partial_ratio(term, all_keywords)
            if best_score < 70:  # Threshold for fuzzy matching
                return False
                
        return True
        return any(search_term in term for term in self.keywords)


class CommandItemDelegate(QStyledItemDelegate):
    """Custom delegate for rendering command items."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon_size = QSize(16, 16)
        self._padding = 4
    
    def paint(self, painter, option, index):
        """Paint the command item or category header."""
        # Draw selection highlight (only for selectable items)
        if index.flags() & Qt.ItemFlag.ItemIsSelectable:
            option.widget.style().drawPrimitive(
                QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter, option.widget
            )
        
        # Get item data
        data = index.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        rect = option.rect.adjusted(self._padding, self._padding, -self._padding, -self._padding)
        
        # Set up painter
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        
        # Handle category headers (strings)
        if isinstance(data, str):
            # Draw category header
            text_rect = rect.adjusted(8, 0, -8, 0)
            font = option.font
            font.setBold(True)
            painter.setFont(font)
            
            # Draw text with a subtle background
            painter.setPen(QColor(option.palette.color(QPalette.ColorRole.Text).darker(200)))
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                data
            )
            
            # Draw a subtle line under the category
            line_y = rect.bottom() - 2
            painter.setPen(QColor(option.palette.color(QPalette.ColorRole.Mid).lighter(120)))
            painter.drawLine(rect.left() + 8, line_y, rect.right() - 8, line_y)
            
            painter.restore()
            return
            
        # Handle CommandItem objects
        if hasattr(data, 'name') and hasattr(data, 'description'):
            # Draw icon if available
            icon_rect = rect.adjusted(0, 0, 0, 0)
            icon_rect.setWidth(16)
            
            # TODO: Load icon from theme or resource
            # if data.icon:
            #     icon = QIcon.fromTheme(data.icon, QIcon(f":/icons/{data.icon}.png"))
            #     if not icon.isNull():
            #         icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # Draw command name
            text_rect = rect.adjusted(24, 0, -100, -16)
            name_font = option.font
            name_font.setBold(True)
            painter.setFont(name_font)
            
            # Set text color based on selection state
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(option.palette.color(QPalette.ColorRole.HighlightedText))
            else:
                painter.setPen(option.palette.color(QPalette.ColorRole.Text))
                
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                data.name
            )
            
            # Draw shortcut
            if data.shortcut:
                shortcut_rect = rect.adjusted(rect.width() - 100, 0, -self._padding, -16)
                painter.setFont(option.font)
                if option.state & QStyle.StateFlag.State_Selected:
                    painter.setPen(option.palette.color(QPalette.ColorRole.HighlightedText).lighter(150))
                else:
                    painter.setPen(QColor(option.palette.color(QPalette.ColorRole.Text).lighter(150)))
                painter.drawText(
                    shortcut_rect,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    data.shortcut
                )
            
            # Draw description
            desc_rect = rect.adjusted(24, 16, -self._padding, -self._padding)
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(option.palette.color(QPalette.ColorRole.HighlightedText).darker(125))
            else:
                painter.setPen(QColor(option.palette.color(QPalette.ColorRole.Text).darker(150)))
                
            painter.drawText(
                desc_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                data.description
            )
        
        painter.restore()
    
    def sizeHint(self, option, index):
        """Return the size hint for the item.
        
        Handles both CommandItem objects and string category headers.
        """
        data = index.data(Qt.ItemDataRole.UserRole)
        if not data:
            return super().sizeHint(option, index)
            
        fm = QFontMetrics(option.font)
        width = option.rect.width()
        
        # Handle category headers (strings)
        if isinstance(data, str):
            text_width = width - self._padding * 2
            text_rect = fm.boundingRect(0, 0, text_width, 0, 
                                      Qt.TextFlag.TextWordWrap, data)
            return QSize(width, text_rect.height() + self._padding * 2)
            
        # Handle CommandItem objects
        if hasattr(data, 'name') and hasattr(data, 'description'):
            # Calculate height based on text content
            text_width = width - 24 - self._padding * 2  # Account for icon and padding
            name_rect = fm.boundingRect(0, 0, text_width, 0, 
                                      Qt.TextFlag.TextWordWrap, data.name)
            desc_rect = fm.boundingRect(0, 0, text_width, 0, 
                                     Qt.TextFlag.TextWordWrap, data.description)
            
            height = max(16, name_rect.height()) + max(14, desc_rect.height()) + self._padding * 3
            return QSize(width, height)
            
        # Fallback for other data types
        return super().sizeHint(option, index)


class CommandPalette(QWidget):
    """Command palette widget for quick actions."""
    
    # Signals
    activated = pyqtSignal(str)  # Emitted when a command is activated
    command_triggered = pyqtSignal(CommandItem)  # Emitted with the command item
    
    def __init__(self, parent=None):
        """Initialize the command palette."""
        super().__init__(parent, Qt.WindowType.Popup)
        self._commands: Dict[str, CommandItem] = {}
        self._categories: Set[str] = set()
        self._current_filter = ""
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_style()
    
    def _setup_style(self) -> None:
        """Set up the widget style."""
        self.setStyleSheet("""
            QWidget {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 4px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid palette(mid);
                border-radius: 4px;
                background: palette(base);
                color: palette(text);
            }
            QListView {
                border: 1px solid palette(mid);
                border-radius: 4px;
                background: palette(base);
                alternate-background-color: palette(alternate-base);
            }
            QListView::item {
                padding: 8px;
                border-bottom: 1px solid palette(midlight);
            }
            QListView::item:selected {
                background: palette(highlight);
                color: palette(highlighted-text);
            }
        """)
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Command Palette")
        self.setMinimumWidth(600)
        self.setMaximumHeight(500)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type a command or search...")
        self.search_edit.textChanged.connect(self._filter_commands)
        self.search_edit.installEventFilter(self)
        layout.addWidget(self.search_edit)
        
        # Command list with custom delegate
        self.command_list = QListView()
        self.command_list.setItemDelegate(CommandItemDelegate(self))
        self.command_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.command_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.command_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.command_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.command_list.setAlternatingRowColors(True)
        self.command_list.setUniformItemSizes(False)
        self.command_list.doubleClicked.connect(self._on_item_activated)
        
        # Set up model and proxy model for filtering
        self.model = QStandardItemModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterRole(Qt.ItemDataRole.UserRole)
        self.command_list.setModel(self.proxy_model)
        
        layout.addWidget(self.command_list, 1)
        
        # Status bar
        self.status_bar = QLabel()
        self.status_bar.setStyleSheet("color: palette(mid); font-size: 11px; padding: 2px;")
        layout.addWidget(self.status_bar)
        
        # Set focus to search box
        self.search_edit.setFocus()
        
        # Update status
        self._update_status()
    
    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Close with Escape
        QShortcut(QKeySequence("Esc"), self, self.close)
        
        # Navigate with arrow keys
        QShortcut(QKeySequence("Down"), self, 
                 lambda: self._navigate(1) if self.isVisible() else None)
        QShortcut(QKeySequence("Up"), self, 
                 lambda: self._navigate(-1) if self.isVisible() else None)
        QShortcut(QKeySequence("PageDown"), self,
                 lambda: self._navigate(10) if self.isVisible() else None)
        QShortcut(QKeySequence("PageUp"), self,
                 lambda: self._navigate(-10) if self.isVisible() else None)
        QShortcut(QKeySequence("Home"), self,
                 lambda: self._navigate_to_first() if self.isVisible() else None)
        QShortcut(QKeySequence("End"), self,
                 lambda: self._navigate_to_last() if self.isVisible() else None)
        
        # Execute with Enter
        QShortcut(QKeySequence("Return"), self, 
                 lambda: self._execute_selected() if self.isVisible() else None)
    
    def _navigate(self, delta: int) -> None:
        """Navigate through commands."""
        current = self.command_list.currentIndex()
        if not current.isValid() and delta > 0:
            current = self.proxy_model.index(0, 0)
        else:
            row = max(0, min(
                self.proxy_model.rowCount() - 1,
                current.row() + delta
            ))
            current = self.proxy_model.index(row, 0)
        
        if current.isValid():
            self.command_list.setCurrentIndex(current)
            self.command_list.scrollTo(current, QAbstractItemView.ScrollHint.PositionAtCenter)
    
    def _navigate_to_first(self) -> None:
        """Navigate to the first command."""
        if self.proxy_model.rowCount() > 0:
            index = self.proxy_model.index(0, 0)
            self.command_list.setCurrentIndex(index)
            self.command_list.scrollToTop()
    
    def _navigate_to_last(self) -> None:
        """Navigate to the last command."""
        if self.proxy_model.rowCount() > 0:
            last_index = self.proxy_model.index(self.proxy_model.rowCount() - 1, 0)
            self.command_list.setCurrentIndex(last_index)
            self.command_list.scrollTo(last_index, QAbstractItemView.ScrollHint.PositionAtBottom)
            
    def _on_item_activated(self, index: QModelIndex) -> None:
        """Handle item activation (double-click or Enter)."""
        if not index.isValid():
            return
            
        # Get the source index from the proxy model
        source_index = self.proxy_model.mapToSource(index)
        if not source_index.isValid():
            return
            
        # Get the command item and execute it
        command = self.model.itemFromIndex(source_index).data(Qt.ItemDataRole.UserRole)
        if command and command.handler:
            self.hide()
            command.handler()
            self.command_triggered.emit(command)
    
    def _update_status(self) -> None:
        """Update the status bar with command count."""
        total = self.model.rowCount()
        visible = self.proxy_model.rowCount()
        
        if self._current_filter:
            self.status_bar.setText(f"{visible} of {total} commands")
        else:
            self.status_bar.setText(f"{total} commands")
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Handle key events for the search box."""
        if obj == self.search_edit and event.type() == QEvent.Type.KeyPress:
            key_event = QKeyEvent(event)
            
            # Navigate command list with arrow keys
            if key_event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up, 
                                 Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
                self.command_list.setFocus()
                QApplication.sendEvent(self.command_list, event)
                return True
                
            # Execute selected command with Enter
            if (key_event.key() == Qt.Key.Key_Return and 
                key_event.modifiers() == Qt.KeyboardModifier.NoModifier):
                self._execute_selected()
                return True
                
            # Close with Escape
            if key_event.key() == Qt.Key.Key_Escape:
                self.close()
                return True
                
        return super().eventFilter(obj, event)
    
    def _filter_commands(self, text: str):
        """Filter commands based on search text using fuzzy matching."""
        self._current_filter = text.strip()
        
        # If empty search, show all commands
        if not self._current_filter:
            self._update_commands()
            self._update_status()
            return
            
        # Get all commands and their display text for fuzzy matching
        commands = list(self._commands.values())
        display_texts = [
            f"{cmd.category} {cmd.name} {cmd.description}" 
            for cmd in commands
        ]
        
        # Get best matches using fuzzy search
        matches = process.extract(
            self._current_filter,
            display_texts,
            scorer=fuzz.token_sort_ratio,
            limit=len(commands)
        )
        
        # Filter and sort commands based on fuzzy match scores
        filtered_commands = [
            cmd for cmd, score, _ in sorted(
                [(commands[i], score, idx) for (text, score, idx) in matches 
                 if score > 50],  # Minimum score threshold
                key=lambda x: (-x[1], x[2])  # Sort by score (desc), then original index
            )
        ]
        
        # Update the command list with filtered results
        self._update_commands(filtered_commands)
        self._update_status()
    
    def _update_commands(self, commands: Optional[List[CommandItem]] = None) -> None:
        """Update the command list in the UI.
        
        Args:
            commands: Optional list of commands to display. If None, all commands are shown.
        """
        self.model.clear()
        
        # If no commands provided, use all commands
        if commands is None:
            commands = list(self._commands.values())
        
        # Group commands by category
        categories: Dict[str, List[CommandItem]] = {}
        for cmd in commands:
            category = cmd.category or "General"
            if category not in categories:
                categories[category] = []
            categories[category].append(cmd)
        
        # Add commands to the model, grouped by category
        for category, cmds in sorted(categories.items()):
            # Add category header if there are multiple categories
            if len(categories) > 1:
                category_item = QStandardItem(f"--- {category} ---")
                category_item.setData(category, Qt.ItemDataRole.UserRole)
                category_item.setSelectable(False)
                self.model.appendRow(category_item)
            
            # Add commands for this category
            for cmd in sorted(cmds, key=lambda c: c.name):
                item = QStandardItem()
                item.setData(cmd, Qt.ItemDataRole.UserRole)
                self.model.appendRow(item)
        
        # Update the status bar
        self._update_status()
        
        # Select the first item if available
        if self.proxy_model.rowCount() > 0:
            self.command_list.setCurrentIndex(self.proxy_model.index(0, 0))
    
    def clear_commands(self) -> None:
        """Clear all commands."""
        self._commands.clear()
        self._categories.clear()
        self.model.clear()
        self._update_status()
    
    def get_commands(self) -> List[CommandItem]:
        """Get all commands."""
        return list(self._commands.values())
    
    def get_categories(self) -> Set[str]:
        """Get all categories."""
        return set(self._categories)
