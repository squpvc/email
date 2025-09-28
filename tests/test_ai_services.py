"""
Test cases for AI services.

This module contains unit tests for the AI services module.
"""

import os
import sys
import unittest
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import patch, MagicMock, ANY, PropertyMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the OpenAI API key before importing the services
os.environ["OPENAI_API_KEY"] = "test-key-123"

# Import the module to patch
import phoenix.ai.services as ai_services
from phoenix.ai.services import AIService, EmailSummary, EmailCategory, EmailPriority, EmailClassification, EmailSearchResult


class TestAIService(unittest.TestCase):
    """Test cases for the AIService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample email data for testing
        self.sample_email = {
            "id": "test-email-123",
            "subject": "Test Email Subject",
            "body": "This is a test email body. It contains some sample text for testing purposes.",
            "sender": "test@example.com",
            "date": "2023-12-01T10:00:00Z",
            "recipients": ["recipient@example.com"],
            "has_attachments": False,
            "is_read": False
        }
        
        # Create mock objects
        self.mock_embedding = MagicMock()
        self.mock_embedding.encode.return_value = [0.1] * 384  # Mock embedding vector
        
        self.mock_nlp = MagicMock()
        self.mock_chroma = MagicMock()
        self.mock_openai = MagicMock()
        self.mock_collection = MagicMock()
        
        # Configure the mock OpenAI client
        self.mock_message = MagicMock()
        self.mock_message.content = json.dumps({"summary": "Test summary", "key_points": ["Point 1", "Point 2"]})
        
        self.mock_choice = MagicMock()
        self.mock_choice.message = self.mock_message
        
        self.mock_completion = MagicMock()
        self.mock_completion.choices = [self.mock_choice]
        
        self.mock_openai.chat.completions.create.return_value = self.mock_completion
        
        # Set up the mock collection
        self.mock_collection.upsert.return_value = True
        self.mock_collection.query.return_value = {
            "ids": [["test123"]],
            "distances": [[0.1]],
            "metadatas": [[{"subject": "Test Subject"}]]
        }
        
        # Patch the module-level variables
        self.patchers = [
            patch('phoenix.ai.services.embedding_model', self.mock_embedding),
            patch('phoenix.ai.services.nlp', self.mock_nlp),
            patch('phoenix.ai.services.chroma_client', self.mock_chroma),
            patch('phoenix.ai.services.openai_client', self.mock_openai),
            patch('phoenix.ai.services.collection', self.mock_collection),
            patch('phoenix.ai.services.AI_AVAILABLE', True)
        ]
        
        for patcher in self.patchers:
            patcher.start()
        
        # Create the service after patching
        self.ai_service = AIService()
    
    def tearDown(self):
        """Clean up after each test."""
        for patcher in self.patchers:
            patcher.stop()
        self.ai_service.nlp = self.mock_nlp
        self.ai_service.collection = self.mock_collection
        
        # Sample email data
        self.sample_email = {
            "id": "test123",
            "subject": "Test Email",
            "body": "This is a test email body.",
            "sender": "test@example.com",
            "date": "2023-01-01T12:00:00",
            "recipients": ["recipient@example.com"],
            "has_attachments": False,
            "is_read": False
        }
        
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
    
    def test_summarize_email_success(self):
        """Test successful email summarization."""
        # Configure the mock response for summarization
        self.mock_message.content = json.dumps({
            "summary": "Test summary",
            "key_points": ["Point 1", "Point 2"]
        })
        
        # Mock the _call_openai method to return our test response as a JSON string
        with patch.object(self.ai_service, '_call_openai') as mock_call_openai:
            mock_call_openai.return_value = json.dumps({
                "summary": "Test summary",
                "key_points": ["Point 1", "Point 2"]
            })
            
            # Call the method
            result = self.ai_service.summarize_email(
                subject=self.sample_email["subject"],
                body=self.sample_email["body"]
            )
        
        # Assertions - check that we got an EmailSummary object with the expected attributes
        self.assertIsNotNone(result)
        self.assertIsInstance(result, EmailSummary)
        self.assertEqual(result.summary, "Test summary")
        self.assertEqual(len(result.key_points), 2)
        self.assertEqual(result.key_points[0], "Point 1")
        self.assertEqual(result.key_points[1], "Point 2")
    
    def test_summarize_email_fallback(self):
        """Test email summarization fallback when OpenAI fails."""
        # Mock the _call_openai method to raise an exception
        with patch.object(self.ai_service, '_call_openai') as mock_call_openai:
            mock_call_openai.side_effect = Exception("API error")
            
            # Call the method
            result = self.ai_service.summarize_email(
                subject=self.sample_email["subject"],
                body=self.sample_email["body"]
            )
        
        # Assertions - should return a basic summary with the body as fallback
        self.assertIsNotNone(result)
        self.assertIsInstance(result, EmailSummary)
        self.assertIn(self.sample_email["body"], result.summary)
        self.assertEqual(len(result.key_points), 0)
    
    def test_classify_email(self):
        """Test email classification."""
        # Configure the mock response for classification
        mock_response = {
            "category": "work",
            "priority": "high",
            "sentiment": "neutral",
            "confidence": 0.9
        }
        self.mock_message.content = json.dumps(mock_response)
    
        # Call the method
        result = self.ai_service.classify_email(
            subject=self.sample_email["subject"],
            body=self.sample_email["body"],
            sender=self.sample_email["sender"]
        )
    
        # Assertions
        self.assertIsNotNone(result)
        self.assertIn("category", result)
        self.assertIn("priority", result)
        self.assertIn("sentiment", result)
        self.assertEqual(result.category, EmailCategory.PRIMARY)
        self.assertEqual(result.priority, EmailPriority.NORMAL)
        self.assertIn("meeting", result.tags)
    
    def test_suggest_reply(self):
        """Test reply suggestion."""
        # Mock the OpenAI response for reply suggestion
        mock_reply = "Thank you for the update. I'll be there for the meeting."
        self.mock_message.content = mock_reply
    
        # Call the method
        result = self.ai_service.suggest_reply(
            email_subject=self.sample_email["subject"],
            email_body=self.sample_email["body"]
        )
    
        # Assertions
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
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
        self.mock_message.content = json.dumps(mock_response)
    
        # Call the method
        result = self.ai_service.extract_action_items(
            email_subject=self.sample_email["subject"],
            email_body=self.sample_email["body"]
        )
    
        # Assertions
        self.assertIsInstance(result, list)
        if result:  # Only check contents if list is not empty
            self.assertIn("action", result[0])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action"], "Prepare project update")
        self.assertEqual(result[0]["priority"], "high")
    
    def test_index_and_search_emails(self):
        """Test email indexing and searching."""
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
        search_results = self.ai_service.search_emails("test query", limit=5)
        self.assertIsInstance(search_results, list)
        self.assertEqual(search_results[0].subject, self.sample_email["subject"])


if __name__ == "__main__":
    unittest.main()
