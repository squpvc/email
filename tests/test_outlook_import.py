"""
Tests for the Outlook import functionality.
"""
import os
import tempfile
import unittest
import sys
from unittest.mock import MagicMock, patch, ANY

# Check if PyQt6 is available
HAS_PYQT6 = False
try:
    from PyQt6.QtWidgets import QApplication
    HAS_PYQT6 = True
except ImportError:
    pass

# Only import these if we have PyQt6
if HAS_PYQT6:
    from phoenix.commands.outlook_import import OutlookImportCommand
    from phoenix.database import get_db_session
    from phoenix.models.outlook_import import OutlookImport, OutlookImportMapping

# Check if pypff is available
HAS_PYPFF = False
try:
    import pypff  # noqa: F401
    HAS_PYPFF = True
except ImportError:
    pass


@unittest.skipIf(not HAS_PYPFF, "pypff-python not installed")
class TestOutlookImport(unittest.TestCase):
    """Test cases for Outlook import functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Initialize QApplication if it doesn't exist
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.temp_dir.name, "test.pst")
        
        # Create a dummy PST file for testing
        with open(self.test_file, 'wb') as f:
            f.write(b'Dummy PST file content')
        
        # Mock application
        self.app_mock = MagicMock()
        self.app_mock.activeWindow.return_value = MagicMock()
        self.app_mock.current_user = MagicMock()
        self.app_mock.current_user.id = 1
        
        # Create command instance
        self.command = OutlookImportCommand()

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_command_initialization(self):
        """Test command initialization."""
        self.assertEqual(self.command.name, "Import from Outlook")
        self.assertEqual(self.command.description, "Import emails from Outlook PST/OST files")
        self.assertEqual(self.command.shortcut, "Ctrl+Shift+O")
        self.assertTrue(self.command.is_available)

    @patch('phoenix.ui.dialogs.outlook_import_dialog.show_outlook_import_dialog')
    def test_execute(self, mock_show_dialog):
        """Test command execution."""
        self.command.execute(self.app_mock)
        mock_show_dialog.assert_called_once_with(
            parent=self.app_mock.activeWindow(),
            db_session_factory=ANY,
            user_id=1
        )

    @patch('pypff.file')
    def test_import_dialog_initialization(self, mock_pff):
        """Test outlook import dialog initialization."""
        from phoenix.ui.dialogs.outlook_import_dialog import OutlookImportDialog
        
        # Create a mock PST file
        mock_pff.return_value = MagicMock()
        
        # Create dialog
        dialog = OutlookImportDialog(
            parent=None,
            db_session_factory=get_db_session,
            user_id=1
        )
        
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.windowTitle(), "Import from Outlook")

    @patch('pypff.file')
    def test_import_process(self, mock_pff):
        """Test the import process with a mock PST file."""
        from phoenix.ui.dialogs.outlook_import_dialog import OutlookImportDialog
        
        # Setup mock PST file structure
        mock_folder = MagicMock()
        mock_folder.name = "Inbox"
        mock_folder.number_of_sub_messages = 1
        mock_folder.get_sub_messages.return_value = [MagicMock()]
        
        mock_pff.return_value = MagicMock()
        mock_pff.return_value.get_root_folder.return_value = mock_folder
        
        # Create dialog
        dialog = OutlookImportDialog(
            parent=None,
            db_session_factory=get_db_session,
            user_id=1
        )
        
        # Test file selection
        dialog.ui.filePathEdit.setText(self.test_file)
        dialog._on_browse_clicked()
        
        # Test folder mapping
        model = dialog.folder_model
        self.assertEqual(model.rowCount(), 1)
        
        # Test import
        dialog._on_import_clicked()
        
        # Verify database records
        with get_db_session() as session:
            imports = session.query(OutlookImport).all()
            self.assertEqual(len(imports), 1)
            self.assertEqual(imports[0].file_path, self.test_file)
            
            mappings = session.query(OutlookImportMapping).all()
            self.assertGreaterEqual(len(mappings), 1)


if __name__ == '__main__':
    unittest.main()
