"""
Settings dialog for Project Phoenix.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPalette, QFont
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QWidget, QListWidget, QPushButton,
    QHBoxLayout, QFormLayout, QComboBox, QSpinBox, QColorDialog, QMessageBox,
    QLineEdit, QCheckBox, QDialogButtonBox, QSizePolicy, QSpacerItem, QListWidgetItem,
    QLabel
)

from phoenix.utils.theme import get_theme_names
from phoenix.application import PhoenixApplicationBase

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """Application settings dialog."""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, app: PhoenixApplicationBase, parent: Optional[QWidget] = None):
        """Initialize the settings dialog.
        
        Args:
            app: The main application instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.app = app
        self._initial_settings: Dict[str, Any] = {}
        
        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 500)
        
        self._setup_ui()
        self._load_settings()
        
        # Store initial settings for cancel operation
        self._initial_settings = self._get_current_settings()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        
        # Tab widget for different settings categories
        self.tabs = QTabWidget()
        
        # Appearance tab
        appearance_tab = QWidget()
        self._setup_appearance_tab(appearance_tab)
        self.tabs.addTab(appearance_tab, "Appearance")
        
        # Email accounts tab
        email_tab = QWidget()
        self._setup_email_accounts_tab(email_tab)
        self.tabs.addTab(email_tab, "Email Accounts")
        
        main_layout.addWidget(self.tabs)
        
        # Dialog buttons
        button_box = QHBoxLayout()
        button_box.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self._on_apply)
        self.apply_button.setEnabled(False)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self._on_ok)
        
        button_box.addWidget(self.cancel_button)
        button_box.addWidget(self.apply_button)
        button_box.addWidget(self.ok_button)
        
        main_layout.addLayout(button_box)
        
        # Connect signals
        self.tabs.currentChanged.connect(self._on_tab_changed)
    
    def _setup_email_accounts_tab(self, parent: QWidget) -> None:
        """Set up the email accounts management tab."""
        layout = QVBoxLayout(parent)
        
        # Email accounts list
        self.accounts_list = QListWidget()
        self.accounts_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(QLabel("Email Accounts:"))
        layout.addWidget(self.accounts_list)
        
        # Buttons for account management
        button_layout = QHBoxLayout()
        
        self.add_account_btn = QPushButton("Add Account...")
        self.add_account_btn.clicked.connect(self._on_add_account)
        
        self.edit_account_btn = QPushButton("Edit")
        self.edit_account_btn.clicked.connect(self._on_edit_account)
        self.edit_account_btn.setEnabled(False)
        
        self.remove_account_btn = QPushButton("Remove")
        self.remove_account_btn.clicked.connect(self._on_remove_account)
        self.remove_account_btn.setEnabled(False)
        
        button_layout.addWidget(self.add_account_btn)
        button_layout.addWidget(self.edit_account_btn)
        button_layout.addWidget(self.remove_account_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Connect signals using lambda to pass self
        self.accounts_list.itemSelectionChanged.connect(lambda: self._on_account_selected())
        self.add_account_btn.clicked.connect(lambda: asyncio.create_task(self._on_add_account()))
        self.edit_account_btn.clicked.connect(lambda: asyncio.create_task(self._on_edit_account()))
        self.remove_account_btn.clicked.connect(lambda: asyncio.create_task(self._on_remove_account()))
        
        # Initial button state
        self._on_account_selected()
        
        # Load existing accounts
        self._load_email_accounts()
    
    async def _load_email_accounts(self) -> None:
        """Load email accounts from the database."""
        self.accounts_list.clear()
        
        try:
            from ...services.email_account_service import email_account_service
            accounts = await email_account_service.get_all_accounts()
            
            for account in accounts:
                display_text = f"{account.display_name} <{account.email}>" if account.display_name else account.email
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, account.id)  # Store account ID in item data
                self.accounts_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error loading email accounts: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load email accounts: {e}",
                QMessageBox.StandardButton.Ok
            )
    
    async def _on_add_account(self) -> None:
        """Handle add account button click."""
        from ...services.email_account_service import email_account_service
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Email Account")
        dialog.setMinimumWidth(400)
        layout = QFormLayout(dialog)
        
        # Form fields
        name_edit = QLineEdit()
        email_edit = QLineEdit()
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        # IMAP settings
        imap_server_edit = QLineEdit()
        imap_port_edit = QSpinBox()
        imap_port_edit.setRange(1, 65535)
        imap_port_edit.setValue(993)
        imap_ssl_check = QCheckBox("Use SSL/TLS")
        imap_ssl_check.setChecked(True)
        
        # SMTP settings
        smtp_server_edit = QLineEdit()
        smtp_port_edit = QSpinBox()
        smtp_port_edit.setRange(1, 65535)
        smtp_port_edit.setValue(587)
        smtp_ssl_check = QCheckBox("Use SSL/TLS")
        smtp_ssl_check.setChecked(True)
        smtp_tls_check = QCheckBox("Use STARTTLS")
        smtp_tls_check.setChecked(True)
        
        # SMTP authentication (if different from main credentials)
        smtp_username_edit = QLineEdit()
        
        # Add fields to form
        layout.addRow("<b>Account Information</b>")
        layout.addRow("Display Name:", name_edit)
        layout.addRow("Email Address:", email_edit)
        layout.addRow("Password:", password_edit)
        
        layout.addItem(QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addRow("<b>IMAP Settings</b>")
        layout.addRow("IMAP Server:", imap_server_edit)
        layout.addRow("IMAP Port:", imap_port_edit)
        layout.addRow("", imap_ssl_check)
        
        layout.addItem(QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addRow("<b>SMTP Settings</b>")
        layout.addRow("SMTP Server:", smtp_server_edit)
        layout.addRow("SMTP Port:", smtp_port_edit)
        layout.addRow("SMTP Username:", smtp_username_edit)
        layout.addRow("", smtp_ssl_check)
        layout.addRow("", smtp_tls_check)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        # Auto-fill server settings based on email domain
        def update_server_settings():
            email = email_edit.text().strip()
            if '@' in email:
                domain = email.split('@')[1].lower()
                
                # Common email providers
                if 'gmail' in domain:
                    imap_server_edit.setText('imap.gmail.com')
                    smtp_server_edit.setText('smtp.gmail.com')
                    smtp_port_edit.setValue(465)
                    smtp_ssl_check.setChecked(True)
                    smtp_tls_check.setChecked(False)
                elif 'outlook' in domain or 'hotmail' in domain or 'live' in domain:
                    imap_server_edit.setText('outlook.office365.com')
                    smtp_server_edit.setText('smtp.office365.com')
                    smtp_port_edit.setValue(587)
                    smtp_ssl_check.setChecked(False)
                    smtp_tls_check.setChecked(True)
                elif 'yahoo' in domain:
                    imap_server_edit.setText('imap.mail.yahoo.com')
                    smtp_server_edit.setText('smtp.mail.yahoo.com')
                    smtp_port_edit.setValue(465)
                    smtp_ssl_check.setChecked(True)
                    smtp_tls_check.setChecked(False)
                
                # Always enable SSL for IMAP
                imap_ssl_check.setChecked(True)
        
        # Connect email field change to auto-fill
        email_edit.textChanged.connect(update_server_settings)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                # Validate required fields
                if not email_edit.text().strip() or not password_edit.text():
                    QMessageBox.warning(
                        self,
                        "Validation Error",
                        "Email and password are required.",
                        QMessageBox.StandardButton.Ok
                    )
                    return
                
                # Create account
                account = await email_account_service.create_account(
                    email=email_edit.text().strip(),
                    password=password_edit.text(),
                    display_name=name_edit.text().strip() or None,
                    imap_server=imap_server_edit.text().strip() or None,
                    imap_port=imap_port_edit.value(),
                    imap_ssl=imap_ssl_check.isChecked(),
                    smtp_server=smtp_server_edit.text().strip() or None,
                    smtp_port=smtp_port_edit.value(),
                    smtp_ssl=smtp_ssl_check.isChecked(),
                    smtp_tls=smtp_tls_check.isChecked(),
                    smtp_username=email_edit.text().strip()  # Default to email
                )
                
                if account:
                    await self._load_email_accounts()  # Refresh the list
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Account {account.email} added successfully.",
                        QMessageBox.StandardButton.Ok
                    )
                else:
                    raise Exception("Failed to create account")
                    
            except Exception as e:
                logger.error(f"Error adding email account: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to add email account: {e}",
                    QMessageBox.StandardButton.Ok
                )
    
    async def _on_edit_account(self) -> None:
        """Handle edit account button click."""
        from ...services.email_account_service import email_account_service
        
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            return
            
        # Get account ID from item data
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not account_id:
            logger.error("No account ID found in selected item")
            return
            
        # Load account details
        account = await email_account_service.get_account(account_id)
        if not account:
            QMessageBox.critical(
                self,
                "Error",
                "Failed to load account details.",
                QMessageBox.StandardButton.Ok
            )
            return
            
        # Create edit dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Email Account")
        dialog.setMinimumWidth(400)
        layout = QFormLayout(dialog)
        
        # Form fields
        name_edit = QLineEdit(account.display_name or "")
        email_edit = QLineEdit(account.email)
        email_edit.setReadOnly(True)  # Don't allow changing email
        
        # Password field (leave empty by default)
        password_edit = QLineEdit()
        password_edit.setPlaceholderText("Leave empty to keep current password")
        password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        # IMAP settings
        imap_server_edit = QLineEdit(account.imap_server or "")
        imap_port_edit = QSpinBox()
        imap_port_edit.setRange(1, 65535)
        imap_port_edit.setValue(account.imap_port or 993)
        imap_ssl_check = QCheckBox("Use SSL/TLS")
        imap_ssl_check.setChecked(account.imap_ssl if account.imap_ssl is not None else True)
        
        # SMTP settings
        smtp_server_edit = QLineEdit(account.smtp_server or "")
        smtp_port_edit = QSpinBox()
        smtp_port_edit.setRange(1, 65535)
        smtp_port_edit.setValue(account.smtp_port or 587)
        smtp_ssl_check = QCheckBox("Use SSL/TLS")
        smtp_ssl_check.setChecked(account.smtp_ssl if account.smtp_ssl is not None else True)
        smtp_tls_check = QCheckBox("Use STARTTLS")
        smtp_tls_check.setChecked(account.smtp_tls if account.smtp_tls is not None else True)
        
        # SMTP authentication (if different from main credentials)
        smtp_username_edit = QLineEdit(account.smtp_username or account.email)
        
        # Add fields to form
        layout.addRow("<b>Account Information</b>")
        layout.addRow("Display Name:", name_edit)
        layout.addRow("Email Address:", email_edit)
        layout.addRow("New Password (optional):", password_edit)
        
        layout.addItem(QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addRow("<b>IMAP Settings</b>")
        layout.addRow("IMAP Server:", imap_server_edit)
        layout.addRow("IMAP Port:", imap_port_edit)
        layout.addRow("", imap_ssl_check)
        
        layout.addItem(QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addRow("<b>SMTP Settings</b>")
        layout.addRow("SMTP Server:", smtp_server_edit)
        layout.addRow("SMTP Port:", smtp_port_edit)
        layout.addRow("SMTP Username:", smtp_username_edit)
        layout.addRow("", smtp_ssl_check)
        layout.addRow("", smtp_tls_check)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                # Prepare updates
                updates = {
                    'display_name': name_edit.text().strip() or None,
                    'imap_server': imap_server_edit.text().strip() or None,
                    'imap_port': imap_port_edit.value(),
                    'imap_ssl': imap_ssl_check.isChecked(),
                    'smtp_server': smtp_server_edit.text().strip() or None,
                    'smtp_port': smtp_port_edit.value(),
                    'smtp_ssl': smtp_ssl_check.isChecked(),
                    'smtp_tls': smtp_tls_check.isChecked(),
                    'smtp_username': smtp_username_edit.text().strip() or None,
                }
                
                # Only update password if provided
                if password_edit.text():
                    updates['password'] = password_edit.text()
                
                # Update account
                success = await email_account_service.update_account(account.id, **updates)
                
                if success:
                    await self._load_email_accounts()  # Refresh the list
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Account {account.email} updated successfully.",
                        QMessageBox.StandardButton.Ok
                    )
                else:
                    raise Exception("Failed to update account")
                    
            except Exception as e:
                logger.error(f"Error updating email account: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to update email account: {e}",
                    QMessageBox.StandardButton.Ok
                )
    
    async def _on_remove_account(self) -> None:
        """Handle remove account button click."""
        from ...services.email_account_service import email_account_service
        
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            return
            
        # Get account ID from item data
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        email = selected_items[0].text()
        
        if not account_id:
            logger.error("No account ID found in selected item")
            return
            
        reply = QMessageBox.question(
            self, 
            "Remove Account",
            f"Are you sure you want to remove the account {email}?\n\n"
            "This will remove all emails and settings for this account.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = await email_account_service.delete_account(account_id)
                if success:
                    await self._load_email_accounts()  # Refresh the list
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Account {email} has been removed.",
                        QMessageBox.StandardButton.Ok
                    )
                else:
                    raise Exception("Failed to delete account")
                    
            except Exception as e:
                logger.error(f"Error removing email account: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to remove email account: {e}",
                    QMessageBox.StandardButton.Ok
                )
    
    def _on_account_selected(self) -> None:
        """Handle account selection change."""
        has_selection = len(self.accounts_list.selectedItems()) > 0
        self.edit_account_btn.setEnabled(has_selection)
        self.remove_account_btn.setEnabled(has_selection)
        
    def _on_setting_changed(self, value=None) -> None:
        """Handle setting changes in the dialog.
        
        Args:
            value: The new value of the setting that changed (optional)
        """
        # Enable the Apply button since settings have been modified
        self.apply_button.setEnabled(True)
    
    def _setup_appearance_tab(self, parent: QWidget) -> None:
        """Set up the appearance settings tab."""
        layout = QFormLayout(parent)
        
        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(get_theme_names())
        self.theme_combo.currentTextChanged.connect(self._on_setting_changed)
        
        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        self.font_size_spin.valueChanged.connect(self._on_setting_changed)
        
        # Custom colors
        self.primary_color_btn = QPushButton()
        self.primary_color_btn.setFixedSize(24, 24)
        self.primary_color_btn.clicked.connect(
            lambda: self._choose_color("primary", self.primary_color_btn)
        )
        
        # Add to layout
        layout.addRow("Theme:", self.theme_combo)
        layout.addRow("Font Size:", self.font_size_spin)
        layout.addRow("Primary Color:", self.primary_color_btn)
        
        # Add stretch to push content to top
        layout.addRow(QWidget())
    
    def _choose_color(self, color_type: str, button: QPushButton) -> None:
        """Open color picker dialog."""
        color = QColorDialog.getColor(
            button.palette().button().color(),
            self,
            f"Choose {color_type.replace('_', ' ').title()} Color"
        )
        
        if color.isValid():
            # Update button color
            button.setStyleSheet(
                f"background-color: {color.name()}; "
                f"border: 1px solid {color.darker(125).name()};"
            )
            self._on_setting_changed()
    
    def _on_tab_changed(self, index: int) -> None:
        """Handle tab changes."""
        # Update UI based on selected tab if needed
        pass
        
    def _load_settings(self) -> None:
        """Load application settings into the dialog."""
        try:
            # Load theme
            theme = self.app.get_setting('theme', 'light')
            if hasattr(self, 'theme_combo') and self.theme_combo.findText(theme) >= 0:
                self.theme_combo.setCurrentText(theme)
                
            # Load font size if available
            if hasattr(self, 'font_size_spin'):
                font_size = self.app.get_setting('font_size')
                if font_size is not None:
                    self.font_size_spin.setValue(font_size)
            
            # Load any other settings as needed
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load settings: {e}",
                QMessageBox.StandardButton.Ok
            )
    
    def _get_current_settings(self) -> Dict[str, Any]:
        """Get the current settings from the dialog."""
        settings = {}
        
        # Get theme setting
        if hasattr(self, 'theme_combo'):
            settings['theme'] = self.theme_combo.currentText()
            
        # Get font size if available
        if hasattr(self, 'font_size_spin'):
            settings['font_size'] = self.font_size_spin.value()
            
        # Add other settings as needed
        
        return settings
        
    async def _load_email_accounts_async(self) -> None:
        """Load email accounts from the database (async version)."""
        try:
            from ...services import email_account_service
            accounts = await email_account_service.get_all_accounts()
            
            self.accounts_list.clear()
            for account in accounts:
                item = QListWidgetItem(account.email)
                item.setData(Qt.ItemDataRole.UserRole, account.id)
                self.accounts_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error loading email accounts: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load email accounts: {e}",
                QMessageBox.StandardButton.Ok
            )
    
    def _load_email_accounts(self) -> None:
        """Load email accounts from the database (synchronous wrapper)."""
        asyncio.create_task(self._load_email_accounts_async())
    
    def _on_apply(self) -> None:
        """Handle Apply button click."""
        try:
            # Save settings
            settings = self._get_current_settings()
            for key, value in settings.items():
                self.app.set_setting(key, value)
            
            # Disable Apply button after saving
            self.apply_button.setEnabled(False)
            
            # Notify that settings have changed
            self.settings_changed.emit()
            
        except Exception as e:
            logger.error(f"Error applying settings: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to apply settings: {e}",
                QMessageBox.StandardButton.Ok
            )
    
    def _on_ok(self) -> None:
        """Handle OK button click."""
        # Apply settings first
        if self.apply_button.isEnabled():
            self._on_apply()
        
        # Close the dialog
        self.accept()
