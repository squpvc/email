"""
Unit tests for the AIService class.

This module contains isolated unit tests for the AIService class.
"""

import os
import sys
import unittest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, ANY

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the OpenAI API key before importing the services
os.environ["OPENAI_API_KEY"] = "test-key-123"

# Now import the services
from phoenix.ai.services import AIService, EmailSummary, EmailCategory, EmailPriority, EmailClassification

class TestAIServiceUnit(unittest.TestCase):
    """Unit tests for the AIService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mocks for all dependencies
        self.mock_embedding = MagicMock()
        self.mock_embedding.encode.return_value = [0.1] * 384  # Mock embedding vector
        
        self.mock_nlp = MagicMock()
        self.mock_chroma = MagicMock()
        self.mock_openai = MagicMock()
        self.mock_collection = MagicMock()
        
        # Configure the mock OpenAI client
        self.mock_completion = MagicMock()
        self.mock_completion.choices[0].message.content = "Test response"
        self.mock_openai.chat.completions.create.return_value = self.mock_completion
        
        # Patch the AI dependencies
        self.patchers = [
            patch('phoenix.ai.services.embedding_model', self.mock_embedding),
            patch('phoenix.ai.services.nlp', self.mock_nlp),
            patch('phoenix.ai.services.chroma_client', self.mock_chroma),
            patch('phoenix.ai.services.openai_client', self.mock_openai),
            patch('phoenix.ai.services.collection', self.mock_collection),
            patch('phoenix.ai.services.AI_AVAILABLE', True)  # Force AI to be available
        ]
        
        for patcher in self.patchers:
            patcher.start()
        
        # Initialize the service with mocked dependencies
        self.ai_service = AIService()
        self.ai_service.available = True  # Force available for testing
        
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
    
    def tearDown(self):
        """Clean up after tests."""
        for patcher in self.patchers:
            patcher.stop()
    
    def test_summarize_email(self):
        """Test email summarization."""
        # Configure the mock response for summarization
        self.mock_completion.choices[0].message.content = "Summary of the email"
        
        # Mock spaCy doc
        mock_doc = MagicMock()
        mock_sent = MagicMock()
        mock_sent.text = "Let's have our weekly sync tomorrow at 10 AM."
        mock_doc.ents = []
        mock_doc.sents = [mock_sent]
        self.mock_nlp.return_value = mock_doc
        
        # Call the method
        result = self.ai_service.summarize_email(
            subject=self.sample_email["subject"],
            body=self.sample_email["body"]
        )
        
        # Assertions
        self.assertIsInstance(result, EmailSummary)
        self.assertEqual(result.summary, "Summary of the email")
        self.assertIn("weekly sync", result.key_points[0])
    
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
        self.mock_completion.choices[0].message.content = json.dumps(mock_response)
        
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
        self.assertIn("meeting", result.tags)
    
    def test_suggest_reply(self):
        """Test reply suggestion."""
        # Mock the OpenAI response for reply suggestion
        mock_reply = "Thank you for the update. I'll be there for the meeting."
        self.mock_completion.choices[0].message.content = mock_reply
        
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
        self.mock_completion.choices[0].message.content = json.dumps(mock_response)
        
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
    
    def test_index_and_search_emails(self):
        """Test email indexing and searching."""
        # Configure mock collection
        self.mock_collection.query.return_value = {
            "ids": [["test123"]],
            "distances": [[0.1]],
            "metadatas": [[{
                "subject": self.sample_email["subject"],
                "sender": self.sample_email["sender"],
                "date": self.sample_email["date"],
                "snippet": self.sample_email["body"][:200] + "...",
                "has_attachments": False,
                "is_read": False,
                "category": "primary",
                "priority": 2,
                "sentiment": "neutral"
            }]],
            "documents": [[self.sample_email["body"]]]
        }
        
        # Test index_email
        result = self.ai_service.index_email(
            email_id=self.sample_email["id"],
            subject=self.sample_email["subject"],
            body=self.sample_email["body"],
            sender=self.sample_email["sender"],
            date=self.sample_email["date"],
            recipients=self.sample_email["recipients"],
            has_attachments=self.sample_email["has_attachments"],
            is_read=self.sample_email["is_read"]
        )
        
        # Assert index was called
        self.assertTrue(result)
        self.mock_collection.upsert.assert_called_once()
        
        # Test search_emails
        search_results = self.ai_service.search_emails("weekly meeting")
        
        # Assert search was called and returned results
        self.mock_collection.query.assert_called()
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0].subject, self.sample_email["subject"])


if __name__ == "__main__":
    unittest.main()
