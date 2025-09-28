"""
Tests for the AI Command Handler.

This module contains tests for the AI command handler functionality.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, ANY

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create a proper mock Command class
class MockCommand:
    def __init__(self, id, name, description, category, **kwargs):
        self.id = id
        self.name = name
        self.description = description
        self.category = category
        for key, value in kwargs.items():
            setattr(self, key, value)

# Mock the necessary modules
sys.modules['phoenix.core.commands'] = MagicMock()
sys.modules['phoenix.core.commands'].Command = MockCommand
sys.modules['phoenix.core.commands'].CommandCategory = MagicMock()

# Mock the AI services
sys.modules['phoenix.ai.services'] = MagicMock()
sys.modules['phoenix.ai.services'].AI_AVAILABLE = True
sys.modules['phoenix.ai.services'].ai_service = MagicMock()
sys.modules['phoenix.ai.services'].EmailSummary = MagicMock()
sys.modules['phoenix.ai.services'].EmailClassification = MagicMock()

# Now import the module under test
with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
    from phoenix.ai.command_handler import AICommand, AICommandHandler

class TestAICommandHandler(unittest.TestCase):
    """Tests for the AICommandHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock AI service
        self.mock_ai_service = MagicMock()

        # Create a test command
        self.test_command = AICommand(
            id="test.command",
            name="Test Command",
            description="A test command",
            category=MagicMock(),
            handler=lambda: {"result": "success"}
        )

        # Patch the AI service import
        self.patcher = patch(
            'phoenix.ai.command_handler.ai_service',
            self.mock_ai_service
        )
        self.patcher.start()

        # Create the handler
        self.handler = AICommandHandler()

        # Mock the signal emissions
        self.handler.command_executed = MagicMock()
        self.handler.error_occurred = MagicMock()
    
    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()
    
    def test_register_command(self):
        """Test registering a command."""
        self.handler.register_command(self.test_command)
        self.assertIn("test.command", self.handler._commands)
        self.assertEqual(self.handler._commands["test.command"], self.test_command)
    
    def test_execute_command_success(self):
        """Test executing a command successfully."""
        # Register the test command
        self.handler.register_command(self.test_command)
        
        # Execute the command
        self.handler.execute_command("test.command")
        
        # Verify the result
        self.handler.command_executed.emit.assert_called_once_with(
            "test.command", {"result": "success"}
        )
        self.handler.error_occurred.emit.assert_not_called()
    
    def test_execute_command_not_found(self):
        """Test executing a non-existent command."""
        self.handler.execute_command("nonexistent.command")
        self.handler.error_occurred.emit.assert_called_once_with(
            "nonexistent.command", "Unknown command: nonexistent.command"
        )
    
    def test_execute_command_with_selection_required(self):
        """Test executing a command that requires selection."""
        # Create a command that requires selection
        cmd = AICommand(
            id="test.selection",
            name="Test Selection",
            description="Test command with selection",
            category=MagicMock(),
            requires_selection=True,
            handler=MagicMock()
        )
        
        self.handler.register_command(cmd)
        
        # Test without selection
        self.handler.execute_command("test.selection")
        self.handler.error_occurred.emit.assert_called_once_with(
            "test.selection", "No text selected"
        )
        
        # Reset mock
        self.handler.error_occurred.reset_mock()
        
        # Test with selection
        self.handler.set_selected_text("Selected text")
        self.handler.execute_command("test.selection")
        self.handler.error_occurred.emit.assert_not_called()
    
    def test_handle_summarize(self):
        """Test the summarize command handler."""
        # Setup test data
        self.handler.set_current_thread({
            "subject": "Test Subject",
            "body": "Test body content"
        })
        
        # Mock the AI service response
        self.mock_ai_service.summarize_email.return_value = MagicMock(
            summary="Test summary",
            key_points=["Point 1", "Point 2"],
            action_items=["Action 1"]
        )
        
        # Execute the command
        result = self.handler._handle_summarize()
        
        # Verify the result
        self.assertEqual(result["type"], "summary")
        self.assertEqual(result["summary"], "Test summary")
        self.assertEqual(len(result["key_points"]), 2)
        self.assertEqual(len(result["action_items"]), 1)
        
        # Verify the service was called correctly
        self.mock_ai_service.summarize_email.assert_called_once_with(
            subject="Test Subject",
            body="Test body content"
        )

if __name__ == "__main__":
    unittest.main()
