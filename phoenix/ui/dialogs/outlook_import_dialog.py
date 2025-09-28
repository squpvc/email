"""
Outlook Import Dialog.

This module provides a dialog for importing emails from Outlook PST/OST files.
"""
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QComboBox, QProgressBar, QMessageBox,
    QSplitter, QHeaderView, QAbstractItemView, QSizePolicy, QWidget, QTabWidget,
    QFormLayout, QLineEdit, QGroupBox, QCheckBox, QSpacerItem, QStyle
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QPixmap, QColor, QPalette

from sqlalchemy.orm import Session

from ...models.email_management import EmailCategory, EmailLabel
from ...importers.outlook import (
    OutlookImporter, create_outlook_import, get_outlook_import,
    delete_outlook_import, list_outlook_imports
)
from ...database import get_db_session
from ...utils.icons import get_icon

logger = logging.getLogger(__name__)


class OutlookImportWorker(QThread):
    """Worker thread for performing the Outlook import."""
    
    progress_updated = pyqtSignal(int, str)  # progress_percent, status_message
    import_finished = pyqtSignal(dict)  # result dict
    
    def __init__(
        self,
        db_session_factory: Callable[[], Session],
        file_path: str,
        folder_mappings: List[Dict[str, Any]],
        user_id: Optional[int] = None
    ):
        super().__init__()
        self.db_session_factory = db_session_factory
        self.file_path = file_path
        self.folder_mappings = folder_mappings
        self.user_id = user_id
        self._is_cancelled = False
    
    def run(self):
        """Run the import process."""
        db = self.db_session_factory()
        try:
            # Create the import record
            self.progress_updated.emit(0, "Initializing import...")
            import_record, error = create_outlook_import(db, self.file_path, self.user_id)
            
            if error or not import_record:
                self.import_finished.emit({"success": False, "error": error or "Failed to create import record"})
                return
            
            # Create the importer
            importer = OutlookImporter(db, self.user_id)
            
            # Open the file
            if not importer.open_file(self.file_path):
                self.import_finished.emit({"success": False, "error": "Could not open Outlook file"})
                return
            
            # Save mappings to the database
            for mapping in self.folder_mappings:
                mapping["import_id"] = import_record.id
            
            # Import emails
            self.progress_updated.emit(5, "Starting import...")
            
            def progress_callback(progress: float):
                if self._is_cancelled:
                    return False
                self.progress_updated.emit(5 + int(progress * 0.9), f"Importing... {int(progress)}%")
                return True
            
            result = importer.import_emails(
                import_id=import_record.id,
                folder_mappings=self.folder_mappings,
                progress_callback=progress_callback
            )
            
            if self._is_cancelled:
                # Update status to cancelled
                import_record = db.query(OutlookImport).get(import_record.id)
                if import_record:
                    import_record.status = "cancelled"
                    db.commit()
                self.import_finished.emit({"success": False, "cancelled": True})
            else:
                self.progress_updated.emit(100, "Import completed successfully!")
                self.import_finished.emit({"success": True, "import_id": import_record.id})
                
        except Exception as e:
            logger.error(f"Error during import: {e}", exc_info=True)
            self.import_finished.emit({"success": False, "error": str(e)})
            
        finally:
            if 'importer' in locals():
                importer.close()
                importer.cleanup()
            db.close()
    
    def cancel(self):
        """Request cancellation of the import."""
        self._is_cancelled = True


class OutlookImportDialog(QDialog):
    """Dialog for importing emails from Outlook PST/OST files."""
    
    def __init__(self, parent=None, db_session_factory=None, user_id=None):
        super().__init__(parent)
        self.db_session_factory = db_session_factory or get_db_session
        self.user_id = user_id
        self.current_import_id = None
        self.worker_thread = None
        self.folder_mappings = []
        
        self.setWindowTitle("Import from Outlook")
        self.setMinimumSize(800, 600)
        self.setWindowIcon(get_icon("mail-import"))
        
        self._init_ui()
        self._load_categories()
    
    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Setup tabs
        self._setup_import_tab()
        self._setup_history_tab()
        
        # Add buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Close")
        self.cancel_button.clicked.connect(self.reject)
        
        self.import_button = QPushButton("Start Import")
        self.import_button.setDefault(True)
        self.import_button.clicked.connect(self._start_import)
        self.import_button.setEnabled(False)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.import_button)
        
        main_layout.addLayout(button_layout)
    
    def _setup_import_tab(self):
        """Set up the import tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # File selection
        file_group = QGroupBox("Outlook File")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a PST or OST file...")
        self.file_path_edit.setReadOnly(True)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_file)
        
        file_layout.addWidget(self.file_path_edit, 1)
        file_layout.addWidget(browse_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        
        self.status_label = QLabel()
        self.status_label.setVisible(False)
        self.status_label.setWordWrap(True)
        
        # Folder mapping
        mapping_group = QGroupBox("Folder Mappings")
        mapping_layout = QVBoxLayout(mapping_group)
        
        # Splitter for folder tree and mapping controls
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Folder tree
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.folder_tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Right side: Mapping controls
        mapping_controls = QWidget()
        mapping_controls_layout = QVBoxLayout(mapping_controls)
        mapping_controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Category selection
        form_layout = QFormLayout()
        
        self.category_combo = QComboBox()
        self.category_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.label_combo = QComboBox()
        self.label_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        form_layout.addRow("Category:", self.category_combo)
        form_layout.addRow("Label:", self.label_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.map_button = QPushButton("Map Selected")
        self.map_button.clicked.connect(self._map_selected_folders)
        self.map_button.setEnabled(False)
        
        self.clear_button = QPushButton("Clear Mapping")
        self.clear_button.clicked.connect(self._clear_mapping)
        self.clear_button.setEnabled(False)
        
        button_layout.addWidget(self.map_button)
        button_layout.addWidget(self.clear_button)
        
        mapping_controls_layout.addLayout(form_layout)
        mapping_controls_layout.addLayout(button_layout)
        mapping_controls_layout.addStretch()
        
        # Add widgets to splitter
        splitter.addWidget(self.folder_tree)
        splitter.addWidget(mapping_controls)
        splitter.setSizes([self.width() * 0.6, self.width() * 0.4])
        
        mapping_layout.addWidget(splitter)
        
        # Add widgets to tab
        layout.addWidget(file_group)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(mapping_group, 1)
        
        # Add tab
        self.tab_widget.addTab(tab, "Import")
    
    def _setup_history_tab(self):
        """Set up the import history tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Import history table
        self.history_table = QTreeWidget()
        self.history_table.setHeaderLabels(["Date", "File", "Status", "Items", ""])  # Empty header for action buttons
        self.history_table.setRootIsDecorated(False)
        self.history_table.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.history_table.setSortingEnabled(True)
        self.history_table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        
        # Configure header
        header = self.history_table.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # File
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Items
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        # Add table to layout
        layout.addWidget(self.history_table)
        
        # Add tab
        self.tab_widget.addTab(tab, "Import History")
        
        # Load history
        self._load_import_history()
    
    def _load_categories(self):
        """Load categories and labels from the database."""
        db = self.db_session_factory()
        try:
            # Load categories
            categories = db.query(EmailCategory).order_by(EmailCategory.name).all()
            
            self.category_combo.clear()
            self.category_combo.addItem("Select a category...", None)
            
            for category in categories:
                self.category_combo.addItem(category.name, category.id)
            
            # Load labels for the first category
            self._update_labels_combo()
            
            # Connect signals
            self.category_combo.currentIndexChanged.connect(self._update_labels_combo)
            
        except Exception as e:
            logger.error(f"Error loading categories: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load categories: {e}")
        finally:
            db.close()
    
    def _update_labels_combo(self):
        """Update the labels combo box based on the selected category."""
        category_id = self.category_combo.currentData()
        
        self.label_combo.clear()
        self.label_combo.addItem("No label", None)
        
        if not category_id:
            return
        
        db = self.db_session_factory()
        try:
            labels = db.query(EmailLabel).filter(
                EmailLabel.category_id == category_id
            ).order_by(EmailLabel.name).all()
            
            for label in labels:
                self.label_combo.addItem(label.name, label.id)
                
        except Exception as e:
            logger.error(f"Error loading labels: {e}")
        finally:
            db.close()
    
    def _browse_file(self):
        """Open a file dialog to select an Outlook file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Outlook File",
            "",
            "Outlook Data Files (*.pst *.ost);;All Files (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self._load_outlook_file(file_path)
    
    def _load_outlook_file(self, file_path: str):
        """Load and analyze an Outlook file."""
        if not file_path or not os.path.isfile(file_path):
            return
        
        self.import_button.setEnabled(False)
        self.folder_tree.clear()
        self.folder_mappings = []
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Analyzing Outlook file...")
        
        # Process in a separate thread to keep the UI responsive
        def analyze_file():
            try:
                importer = OutlookImporter(self.db_session_factory(), self.user_id)
                if importer.open_file(file_path):
                    stats = importer.analyze()
                    importer.close()
                    return stats
                return {"error": "Could not open Outlook file"}
            except Exception as e:
                logger.error(f"Error analyzing Outlook file: {e}", exc_info=True)
                return {"error": str(e)}
        
        def on_analysis_complete(stats):
            self.progress_bar.setVisible(False)
            
            if "error" in stats:
                self.status_label.setText(f"Error: {stats['error']}")
                return
            
            self.status_label.setText(f"Found {stats.get('total_emails', 0)} emails in {stats.get('total_folders', 0)} folders")
            self._populate_folder_tree(stats.get('folders', []))
            self.import_button.setEnabled(True)
        
        # Use QThread to avoid freezing the UI
        self._run_in_thread(analyze_file, on_analysis_complete)
    
    def _populate_folder_tree(self, folders: List[Dict[str, Any]]):
        """Populate the folder tree with Outlook folders."""
        self.folder_tree.clear()
        
        def add_folder(parent_item, folder_info, path=""):
            folder_name = folder_info.get('name', 'Unknown')
            item = QTreeWidgetItem([folder_name])
            
            # Store the full path as data
            item_path = f"{path}/{folder_name}" if path else folder_name
            item.setData(0, Qt.ItemDataRole.UserRole, item_path)
            
            # Set icon
            item.setIcon(0, get_icon("folder"))
            
            # Add to parent
            if parent_item:
                parent_item.addChild(item)
            else:
                self.folder_tree.addTopLevelItem(item)
            
            # Add subfolders
            for subfolder in folder_info.get('subfolders', []):
                add_folder(item, subfolder, item_path)
            
            # Expand top-level items
            if not parent_item:
                item.setExpanded(True)
        
        # Add each top-level folder
        for folder in folders:
            add_folder(None, folder)
        
        # Enable selection
        self.folder_tree.itemSelectionChanged.connect(self._on_folder_selection_changed)
    
    def _on_folder_selection_changed(self):
        """Handle folder selection changes."""
        selected_items = self.folder_tree.selectedItems()
        has_selection = bool(selected_items)
        
        self.map_button.setEnabled(has_selection and bool(self.category_combo.currentData()))
        self.clear_button.setEnabled(has_selection)
    
    def _map_selected_folders(self):
        """Map the selected folders to the selected category/label."""
        selected_items = self.folder_tree.selectedItems()
        if not selected_items:
            return
        
        category_id = self.category_combo.currentData()
        label_id = self.label_combo.currentData()
        
        if not category_id:
            QMessageBox.warning(self, "No Category Selected", "Please select a category first.")
            return
        
        # Update the UI and mappings
        for item in selected_items:
            folder_path = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Check if this folder is already mapped
            mapping = next((m for m in self.folder_mappings if m['source_path'] == folder_path), None)
            
            if mapping:
                # Update existing mapping
                mapping['category_id'] = category_id
                mapping['label_id'] = label_id
            else:
                # Add new mapping
                self.folder_mappings.append({
                    'id': len(self.folder_mappings) + 1,  # Temporary ID
                    'source_path': folder_path,
                    'category_id': category_id,
                    'label_id': label_id,
                    'category_name': self.category_combo.currentText(),
                    'label_name': self.label_combo.currentText() if label_id else None
                })
            
            # Update the item appearance
            self._update_folder_item_style(item, category_id, label_id)
    
    def _clear_mapping(self):
        """Clear the mapping for the selected folders."""
        selected_items = self.folder_tree.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            folder_path = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Remove from mappings
            self.folder_mappings = [m for m in self.folder_mappings if m['source_path'] != folder_path]
            
            # Reset the item style
            self._update_folder_item_style(item, None, None)
    
    def _update_folder_item_style(self, item, category_id, label_id):
        """Update the visual style of a folder item based on its mapping."""
        if category_id:
            # Set bold for mapped items
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            
            # Set tooltip with mapping info
            mapping = next((m for m in self.folder_mappings if m['source_path'] == item.data(0, Qt.ItemDataRole.UserRole)), None)
            if mapping:
                tooltip = f"Mapped to: {mapping['category_name']}"
                if mapping.get('label_name'):
                    tooltip += f" / {mapping['label_name']}"
                item.setToolTip(0, tooltip)
        else:
            # Reset to default style
            font = item.font(0)
            font.setBold(False)
            item.setFont(0, font)
            item.setToolTip(0, "")
    
    def _start_import(self):
        """Start the import process."""
        if not self.folder_mappings:
            QMessageBox.warning(self, "No Mappings", "Please map at least one folder to a category.")
            return
        
        file_path = self.file_path_edit.text()
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.critical(self, "Error", "Please select a valid Outlook file.")
            return
        
        # Confirm before starting
        reply = QMessageBox.question(
            self,
            "Start Import",
            f"Start importing {sum(1 for _ in self.folder_mappings)} mapped folders?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Disable UI during import
        self.import_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.tab_widget.setTabEnabled(0, False)
        
        # Show progress
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Preparing to import...")
        
        # Create and start the worker thread
        self.worker_thread = OutlookImportWorker(
            db_session_factory=self.db_session_factory,
            file_path=file_path,
            folder_mappings=self.folder_mappings,
            user_id=self.user_id
        )
        
        # Connect signals
        self.worker_thread.progress_updated.connect(self._on_import_progress)
        self.worker_thread.import_finished.connect(self._on_import_finished)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        # Start the import
        self.worker_thread.start()
    
    def _on_import_progress(self, progress: int, message: str):
        """Update the progress bar and status message."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
    
    def _on_import_finished(self, result: Dict[str, Any]):
        """Handle import completion."""
        # Re-enable UI
        self.import_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.tab_widget.setTabEnabled(0, True)
        
        if result.get('cancelled'):
            self.status_label.setText("Import was cancelled.")
            QMessageBox.information(self, "Import Cancelled", "The import process was cancelled.")
        elif result.get('success'):
            self.status_label.setText("Import completed successfully!")
            QMessageBox.information(self, "Import Complete", "The import has completed successfully!")
            
            # Refresh history tab
            self._load_import_history()
            
            # Switch to history tab
            self.tab_widget.setCurrentIndex(1)
        else:
            error = result.get('error', 'An unknown error occurred')
            self.status_label.setText(f"Error: {error}")
            QMessageBox.critical(self, "Import Failed", f"The import failed: {error}")
    
    def _load_import_history(self):
        """Load the import history from the database."""
        self.history_table.clear()
        
        db = self.db_session_factory()
        try:
            imports = list_outlook_imports(db, self.user_id)
            
            for import_record in imports:
                # Create item
                item = QTreeWidgetItem([
                    import_record.created_at.strftime("%Y-%m-%d %H:%M"),
                    os.path.basename(import_record.file_path),
                    import_record.status.capitalize(),
                    str(import_record.stats.get('imported_emails', 0) if import_record.stats else 0),
                    ""  # Empty column for actions
                ])
                
                # Store the import ID as data
                item.setData(0, Qt.ItemDataRole.UserRole, import_record.id)
                
                # Add view button
                view_button = QPushButton("View")
                view_button.setProperty("import_id", import_record.id)
                view_button.clicked.connect(self._view_import_details)
                
                # Add delete button
                delete_button = QPushButton("Delete")
                delete_button.setProperty("import_id", import_record.id)
                delete_button.clicked.connect(self._delete_import)
                
                # Add buttons to a widget
                button_widget = QWidget()
                button_layout = QHBoxLayout(button_widget)
                button_layout.setContentsMargins(0, 0, 0, 0)
                button_layout.addWidget(view_button)
                button_layout.addWidget(delete_button)
                button_layout.addStretch()
                
                # Add the item to the table
                self.history_table.addTopLevelItem(item)
                self.history_table.setItemWidget(item, 4, button_widget)
                
        except Exception as e:
            logger.error(f"Error loading import history: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load import history: {e}")
        finally:
            db.close()
    
    def _view_import_details(self):
        """View details of a specific import."""
        button = self.sender()
        import_id = button.property("import_id")
        
        if not import_id:
            return
        
        db = self.db_session_factory()
        try:
            import_record = get_outlook_import(db, import_id)
            if not import_record:
                QMessageBox.warning(self, "Not Found", "The selected import record was not found.")
                return
            
            # Create a dialog to show import details
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Import Details - {os.path.basename(import_record.file_path)}")
            dialog.setMinimumSize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            # Basic info
            info_group = QGroupBox("Import Information")
            info_layout = QFormLayout(info_group)
            
            info_layout.addRow("File:", QLabel(import_record.file_path))
            info_layout.addRow("Status:", QLabel(import_record.status.capitalize()))
            info_layout.addRow("Started:", QLabel(import_record.started_at.strftime("%Y-%m-%d %H:%M") if import_record.started_at else "N/A"))
            info_layout.addRow("Completed:", QLabel(import_record.completed_at.strftime("%Y-%m-%d %H:%M") if import_record.completed_at else "N/A"))
            
            if import_record.error_message:
                error_label = QLabel(import_record.error_message)
                error_label.setWordWrap(True)
                error_label.setStyleSheet("color: red;")
                info_layout.addRow("Error:", error_label)
            
            # Stats
            stats_group = QGroupBox("Statistics")
            stats_layout = QVBoxLayout(stats_group)
            
            if import_record.stats:
                stats_text = f"""
                <table>
                    <tr><td>Total Emails:</td><td>{import_record.stats.get('total_emails', 0)}</td></tr>
                    <tr><td>Imported Emails:</td><td>{import_record.stats.get('imported_emails', 0)}</td></tr>
                    <tr><td>Failed Emails:</td><td>{import_record.stats.get('failed_emails', 0)}</td></tr>
                </table>
                """
                stats_label = QLabel(stats_text)
                stats_label.setTextFormat(Qt.TextFormat.RichText)
                stats_layout.addWidget(stats_label)
            else:
                stats_layout.addWidget(QLabel("No statistics available."))
            
            # Add to layout
            layout.addWidget(info_group)
            layout.addWidget(stats_group)
            
            # Close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            
            # Show the dialog
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error viewing import details: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load import details: {e}")
        finally:
            db.close()
    
    def _delete_import(self):
        """Delete an import record."""
        button = self.sender()
        import_id = button.property("import_id")
        
        if not import_id:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this import record?\n\n"
            "Note: This will only remove the import record, not the imported emails.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Delete the import record
        db = self.db_session_factory()
        try:
            if delete_outlook_import(db, import_id):
                QMessageBox.information(self, "Success", "The import record has been deleted.")
                self._load_import_history()  # Refresh the list
            else:
                QMessageBox.warning(self, "Error", "Could not delete the import record.")
        except Exception as e:
            logger.error(f"Error deleting import record: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete import record: {e}")
        finally:
            db.close()
    
    def _run_in_thread(self, func, callback):
        """Run a function in a separate thread and call the callback with the result."""
        class Worker(QThread):
            finished = pyqtSignal(object)
            
            def run(self):
                try:
                    result = func()
                    self.finished.emit(result)
                except Exception as e:
                    logger.error(f"Error in worker thread: {e}", exc_info=True)
                    self.finished.emit({"error": str(e)})
        
        self.thread = Worker()
        self.thread.finished.connect(callback)
        self.thread.start()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Cancel any running import
        if hasattr(self, 'worker_thread') and self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.cancel()
            self.worker_thread.wait()
        
        event.accept()


def show_outlook_import_dialog(parent=None, db_session_factory=None, user_id=None):
    """Show the Outlook import dialog.
    
    Args:
        parent: Parent widget
        db_session_factory: Function that returns a database session
        user_id: ID of the current user
    """
    dialog = OutlookImportDialog(parent, db_session_factory, user_id)
    dialog.exec()
