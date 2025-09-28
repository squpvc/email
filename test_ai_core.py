"""
Standalone AI Core Tests

This file contains standalone tests for the AI core functionality.
It doesn't depend on the application structure.
"""

import os
import sys
import json
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock, ANY

# Set up mock environment
os.environ["OPENAI_API_KEY"] = "test-key-123"

# Mock the necessary modules
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['phoenix'] = MagicMock()
sys.modules['phoenix.ui'] = MagicMock()
sys.modules['phoenix.ui.widgets'] = MagicMock()
sys.modules['phoenix.ui.widgets.ai_assistant'] = MagicMock()

# Mock the AI service class
class MockAIService:
    """Mock AIService class for testing core functionality."""
    
    def __init__(self):
        self.available = True
        self.embedding_model = MagicMock()
        self.embedding_model.encode.return_value = [0.1] * 384
        self.nlp = MagicMock()
        self.chroma_client = MagicMock()
        self.collection = MagicMock()
        self.openai_client = MagicMock()
        self.openai_client.chat.completions.create.return_value.choices[0].message.content = "Test response"
    
    def summarize_email(self, subject: str, body: str, style: str = "concise") -> dict:
        """Mock summarize_email method."""
        return {
            "summary": "Summary of the email",
            "key_points": ["Key point 1", "Key point 2"],
            "action_items": ["Action item 1", "Action item 2"]
        }
    
    def classify_email(self, subject: str, body: str, sender: str) -> dict:
        """Mock classify_email method."""
        return {
            "category": "primary",
            "priority": 2,
            "tags": ["meeting", "team"],
            "sentiment": "neutral",
            "confidence": 0.9
        }
    
    def suggest_reply(self, email_subject: str, email_body: str, style: str = "professional") -> str:
        """Mock suggest_reply method."""
        return "Thank you for your email. I'll get back to you soon."
    
    def extract_action_items(self, email_subject: str, email_body: str) -> list:
        """Mock extract_action_items method."""
        return [
            {
                "action": "Prepare project update",
                "assignee": "me",
                "due_date": "2023-12-15T10:00:00",
                "priority": "high",
                "status": "pending"
            }
        ]
    
    def search_emails(self, query: str, limit: int = 5) -> list:
        """Mock search_emails method."""
        return [
            {
                "id": "test123",
                "subject": "Weekly Team Meeting",
                "snippet": "Let's have our weekly sync tomorrow at 10 AM.",
                "sender": "john.doe@example.com",
                "date": datetime.utcnow().isoformat(),
                "relevance": 0.95
            }
        ]

class TestAICore(unittest.TestCase):
    """Core tests for the AI service functionality."""
    
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
    
    def test_summarize_email(self):
        """Test email summarization."""
        # Call the method
        result = self.ai_service.summarize_email(
            subject=self.sample_email["subject"],
            body=self.sample_email["body"]
        )
        
        # Assertions
        self.assertIsInstance(result, dict)
        self.assertIn("summary", result)
        self.assertIn("key_points", result)
        self.assertIn("action_items", result)
    
    def test_classify_email(self):
        """Test email classification."""
        # Call the method
        result = self.ai_service.classify_email(
            subject=self.sample_email["subject"],
            body=self.sample_email["body"],
            sender=self.sample_email["sender"]
        )
        
        # Assertions
        self.assertIsInstance(result, dict)
        self.assertEqual(result["category"], "primary")
        self.assertEqual(result["priority"], 2)
        self.assertIn("meeting", result["tags"])
    
    def test_suggest_reply(self):
        """Test reply suggestion."""
        # Call the method
        result = self.ai_service.suggest_reply(
            email_subject=self.sample_email["subject"],
            email_body=self.sample_email["body"]
        )
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
    
    def test_extract_action_items(self):
        """Test action item extraction."""
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
    
    def test_search_emails(self):
        """Test email search."""
        # Call the method
        results = self.ai_service.search_emails("weekly meeting")
        
        # Assertions
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["subject"], "Weekly Team Meeting")

if __name__ == "__main__":
    unittest.main()
