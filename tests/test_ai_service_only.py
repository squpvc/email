"""
AIService Core Tests

This file contains tests for the AIService class in isolation.
"""

import os
import sys
import json
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock, ANY

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the OpenAI API key
os.environ["OPENAI_API_KEY"] = "test-key-123"

# Mock the necessary modules
sys.modules['PyQt6'] = MagicMock()
sys.modules['phoenix.ui'] = MagicMock()
sys.modules['phoenix.ui.widgets'] = MagicMock()
sys.modules['phoenix.ui.widgets.ai_assistant'] = MagicMock()

# Now import the service
from phoenix.ai.services import AIService, EmailSummary, EmailCategory, EmailPriority, EmailClassification

class MockAIService(AIService):
    """Mock AIService with overridden methods to avoid UI dependencies."""
    
    def __init__(self):
        # Skip the parent's __init__ to avoid loading real dependencies
        self.available = True
        self.embedding_model = MagicMock()
        self.embedding_model.encode.return_value = [0.1] * 384
        self.nlp = MagicMock()
        self.chroma_client = MagicMock()
        self.collection = MagicMock()
        self.openai_client = MagicMock()
        self.openai_client.chat.completions.create.return_value.choices[0].message.content = "Test response"

class TestAIServiceCore(unittest.TestCase):
    """Core tests for the AIService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ai_service = MockAIService()
        
        # Sample test data
        self.sample_email = {
            "id": "test123",
            "subject": "Weekly Team Meeting",
            "body": """Hi team,\n            \nLet's have our weekly sync tomorrow at 10 AM.\n\nAgenda:\n1. Project updates\n2. Blockers\n3. Action items\n\nBest regards,\nJohn""",
            "sender": "john.doe@example.com",
            "recipients": ["team@example.com"],
            "date": datetime.utcnow().isoformat(),
            "has_attachments": False,
            "is_read": False
        }
        
        # Mock spaCy doc
        self.mock_doc = MagicMock()
        mock_sent = MagicMock()
        mock_sent.text = "Let's have our weekly sync tomorrow at 10 AM."
        self.mock_doc.ents = []
        self.mock_doc.sents = [mock_sent]
        self.ai_service.nlp.return_value = self.mock_doc
    
    def test_summarize_email(self):
        """Test email summarization."""
        # Configure the mock response for summarization
        self.ai_service.openai_client.chat.completions.create.return_value.choices[0].message.content = "Summary of the email"
        
        # Call the method
        result = self.ai_service.summarize_email(
            subject=self.sample_email["subject"],
            body=self.sample_email["body"]
        )
        
        # Assertions
        self.assertIsInstance(result, EmailSummary)
        self.assertEqual(result.summary, "Summary of the email")
    
    def test_classify_email(self):
        """Test email classification."""
        # Mock the OpenAI response for classification
        mock_response = {
            "category": "primary",
            "priority": 2,
            "tags": "meeting, team",
            "sentiment": "neutral",
            "confidence": 0.9
        }
        self.ai_service.openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_response)
        
        # Call the method
        result = self.ai_service.classify_email(
            subject=self.sample_email["subject"],
            body=self.sample_email["body"],
            sender=self.sample_email["sender"]
        )
        
        # Assertions
        self.assertIsInstance(result, EmailClassification)
        self.assertEqual(result.category, EmailCategory.PRIMARY)
        self.assertEqual(result.priority, EmailPriority.NORMAL)
    
    def test_suggest_reply(self):
        """Test reply suggestion."""
        # Mock the OpenAI response for reply suggestion
        mock_reply = "Thank you for the update. I'll be there for the meeting."
        self.ai_service.openai_client.chat.completions.create.return_value.choices[0].message.content = mock_reply
        
        # Call the method
        result = self.ai_service.suggest_reply(
            email_subject=self.sample_email["subject"],
            email_body=self.sample_email["body"]
        )
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn("meeting", result.lower())
    
    def test_extract_action_items(self):
        """Test action item extraction."""
        # Mock the OpenAI response for action items
        mock_response = {
            "actions": [
                {
                    "action": "Prepare project update",
                    "assignee": "me",
                    "due_date": "2023-12-15T10:00:00",
                    "priority": "high",
                    "status": "pending"
                }
            ]
        }
        self.ai_service.openai_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_response)
        
        # Call the method
        result = self.ai_service.extract_action_items(
            email_subject=self.sample_email["subject"],
            email_body=self.sample_email["body"]
        )
        
        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "Prepare project update")
        self.assertEqual(result[0]["priority"], "high")

if __name__ == "__main__":
    unittest.main()
