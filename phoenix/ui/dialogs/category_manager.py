"""Category and label management dialog."""
from typing import Optional, Dict, List, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QColorDialog, QComboBox, QMessageBox,
    QInputDialog, QWidget, QFormLayout, QCheckBox, QTabWidget, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon, QPainter, QBrush

from ...models.email_management import EmailCategory, EmailLabel
from ...database import DatabaseManager

class ColorButton(QPushButton):
    """A button that shows a color and allows selecting a new color."""
    color_changed = pyqtSignal(QColor)
    
    def __init__(self, color: str = "#808080", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(24, 24)
        self.clicked.connect(self._select_color)
        self._update_icon()
    
    def color(self) -> QColor:
        return self._color
    
    def set_color(self, color: QColor) -> None:
        if self._color != color:
            self._color = color
            self._update_icon()
            self.color_changed.emit(color)
    
    def _select_color(self) -> None:
        color = QColorDialog.getColor(self._color, self, "Select Color")
        if color.isValid():
            self.set_color(color)
    
    def _update_icon(self) -> None:
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self._color))
        painter.setPen(Qt.GlobalColor.gray)
        painter.drawRoundedRect(0, 0, 15, 15, 3, 3)
        painter.end()
        self.setIcon(QIcon(pixmap))

class CategoryEditor(QWidget):
    """Editor for a single category."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._category: Optional[EmailCategory] = None
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Category name")
        layout.addRow("Name:", self.name_edit)
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description")
        layout.addRow("Description:", self.description_edit)
        
        self.color_button = ColorButton()
        layout.addRow("Color:", self.color_button)
        
        self.system_checkbox = QCheckBox("System category")
        self.system_checkbox.setEnabled(False)
        layout.addRow(self.system_checkbox)
    
    def set_category(self, category: Optional[EmailCategory]) -> None:
        self._category = category
        if category:
            self.name_edit.setText(category.name)
            self.description_edit.setText(category.description or "")
            self.color_button.set_color(QColor(category.color))
            self.system_checkbox.setChecked(category.is_system)
            is_system = category.is_system
            self.name_edit.setEnabled(not is_system)
            self.description_edit.setEnabled(not is_system)
            self.color_button.setEnabled(not is_system)
        else:
            self.name_edit.clear()
            self.description_edit.clear()
            self.color_button.set_color(QColor("#808080"))
            self.system_checkbox.setChecked(False)
            self.name_edit.setEnabled(True)
            self.description_edit.setEnabled(True)
            self.color_button.setEnabled(True)
    
    def get_category_data(self) -> Dict[str, Any]:
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.text().strip() or None,
            'color': self.color_button.color().name(),
            'is_system': self.system_checkbox.isChecked()
        }
    
    def validate(self) -> bool:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Category name cannot be empty.")
            return False
        return True

class CategoryManagerDialog(QDialog):
    """Dialog for managing categories and labels."""
    
    def __init__(self, db: DatabaseManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Manage Categories & Labels")
        self.setMinimumSize(800, 600)
        self._init_ui()
        self._load_data()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Categories tab
        self.categories_tab = QWidget()
        self._init_categories_tab()
        tabs.addTab(self.categories_tab, "Categories")
        
        # Labels tab
        self.labels_tab = QWidget()
        self._init_labels_tab()
        tabs.addTab(self.labels_tab, "Labels")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_box = QHBoxLayout()
        button_box.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_box.addWidget(close_btn)
        
        layout.addLayout(button_box)
    
    def _init_categories_tab(self) -> None:
        layout = QHBoxLayout(self.categories_tab)
        
        # Category list
        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(200)
        self.category_list.currentItemChanged.connect(self._on_category_selected)
        
        # Category editor
        self.category_editor = CategoryEditor()
        
        # Buttons
        btn_layout = QVBoxLayout()
        
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_category)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_category)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_category)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        
        # Add widgets to layout
        layout.addWidget(self.category_list)
        layout.addWidget(self.category_editor, 1)
        layout.addLayout(btn_layout)
    
    def _init_labels_tab(self) -> None:
        # Similar to _init_categories_tab but for labels
        pass
    
    def _load_data(self) -> None:
        # Load categories
        self.categories = self.db.query(EmailCategory).order_by(EmailCategory.name).all()
        self._update_category_list()
        
        # Select first category if available
        if self.categories:
            self.category_list.setCurrentRow(0)
    
    def _update_category_list(self) -> None:
        self.category_list.clear()
        for category in self.categories:
            item = QListWidgetItem(category.name)
            item.setData(Qt.ItemDataRole.UserRole, category.id)
            self.category_list.addItem(item)
    
    def _on_category_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        if not current:
            self.category_editor.set_category(None)
            return
            
        category_id = current.data(Qt.ItemDataRole.UserRole)
        category = next((c for c in self.categories if c.id == category_id), None)
        self.category_editor.set_category(category)
    
    def _add_category(self) -> None:
        self.category_list.clearSelection()
        self.category_editor.set_category(None)
        self.name_edit.setFocus()
    
    def _save_category(self) -> None:
        if not self.category_editor.validate():
            return
            
        data = self.category_editor.get_category_data()
        current_item = self.category_list.currentItem()
        
        if current_item:
            # Update existing category
            category_id = current_item.data(Qt.ItemDataRole.UserRole)
            category = next((c for c in self.categories if c.id == category_id), None)
            if category:
                category.name = data['name']
                category.description = data['description']
                category.color = data['color']
                self.db.commit()
                self._load_data()
        else:
            # Add new category
            category = EmailCategory(
                name=data['name'],
                description=data['description'],
                color=data['color'],
                is_system=False
            )
            self.db.add(category)
            self.db.commit()
            self._load_data()
    
    def _delete_category(self) -> None:
        current_item = self.category_list.currentItem()
        if not current_item:
            return
            
        category_id = current_item.data(Qt.ItemDataRole.UserRole)
        category = next((c for c in self.categories if c.id == category_id), None)
        
        if category and not category.is_system:
            # Check if category is in use
            count = self.db.query(EmailCategoryMapping).filter_by(category_id=category_id).count()
            if count > 0:
                QMessageBox.warning(
                    self,
                    "Cannot Delete",
                    f"This category is in use by {count} emails and cannot be deleted."
                )
                return
                
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete the category '{category.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.db.delete(category)
                self.db.commit()
                self._load_data()
