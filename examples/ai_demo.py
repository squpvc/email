"""
AI Features Demo

This script demonstrates the AI capabilities of the Phoenix email client.
It shows how to use the AIService to process and analyze emails.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phoenix.ai.services import AIService, EmailSummary, EmailCategory, EmailPriority


def print_divider(title: str = "") -> None:
    """Print a section divider with optional title."""
    print("\n" + "=" * 80)
    if title:
        print(f"{title.upper():^80}")
        print("=" * 80)
    else:
        print("=" * 80)


def demo_email_processing(ai_service: AIService) -> None:
    """Demonstrate email processing with AI."""
    # Sample email data
    emails = [
        {
            "id": "email1",
            "subject": "Project Deadline Extension",
            "body": """Hello team,

I hope this message finds you well. I wanted to inform you that we've decided to extend the project deadline by one week. The new deadline is now Friday, December 22nd.

This extension should give everyone enough time to complete their tasks without feeling rushed. Please update your schedules accordingly.

Best regards,
Sarah (Project Manager)""",
            "sender": "sarah.manager@company.com",
            "date": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "recipients": ["dev-team@company.com"],
            "has_attachments": False,
            "is_read": False
        },
        {
            "id": "email2",
            "subject": "URGENT: Server Downtime Tonight",
            "body": """Attention all,

We will be performing emergency maintenance on our production servers tonight from 11 PM to 2 AM. During this time, the service will be unavailable.

Impact:
- API endpoints will return 503
- Web interface will show maintenance page
- Email sending/receiving will be delayed

We apologize for the short notice and any inconvenience this may cause.

IT Team""",
            "sender": "it@company.com",
            "date": datetime.utcnow().isoformat(),
            "recipients": ["all@company.com"],
            "has_attachments": True,
            "is_read": True
        }
    ]
    
    # Process each email
    for email in emails:
        print_divider(f"Processing Email: {email['subject']}")
        
        # 1. Index the email
        print("\nIndexing email...")
        ai_service.index_email(
            email_id=email["id"],
            subject=email["subject"],
            body=email["body"],
            sender=email["sender"],
            date=email["date"],
            recipients=email["recipients"],
            has_attachments=email["has_attachments"],
            is_read=email["is_read"]
        )
        
        # 2. Classify the email
        print("\nClassifying email...")
        classification = ai_service.classify_email(
            subject=email["subject"],
            body=email["body"],
            sender=email["sender"],
            recipients=email["recipients"]
        )
        print(f"  Category: {classification.category.value}")
        print(f"  Priority: {classification.priority.name}")
        print(f"  Sentiment: {classification.sentiment}")
        print(f"  Tags: {', '.join(classification.tags) if classification.tags else 'None'}")
        
        # 3. Generate a summary
        print("\nGenerating summary...")
        summary = ai_service.summarize_email(
            subject=email["subject"],
            body=email["body"],
            style="concise"
        )
        print(f"\nSummary:\n{summary.summary}")
        
        # 4. Extract action items
        print("\nExtracting action items...")
        action_items = ai_service.extract_action_items(
            email_subject=email["subject"],
            email_body=email["body"]
        )
        
        if action_items:
            print("\nAction Items:")
            for i, item in enumerate(action_items, 1):
                print(f"  {i}. {item['action']}")
                print(f"     - Priority: {item['priority'].title()}")
                print(f"     - Status: {item['status'].replace('_', ' ').title()}")
                if item['due_date']:
                    print(f"     - Due: {item['due_date']}")
        else:
            print("  No action items found.")
        
        # 5. Suggest a reply
        print("\nGenerating reply suggestion...")
        try:
            reply = ai_service.suggest_reply(
                email_subject=email["subject"],
                email_body=email["body"],
                style="professional",
                tone="appreciative"
            )
            print(f"\nSuggested Reply:\n{reply}")
        except Exception as e:
            print(f"  Could not generate reply: {str(e)}")


def demo_semantic_search(ai_service: AIService) -> None:
    """Demonstrate semantic search capabilities."""
    print_divider("Semantic Search Demo")
    
    # Sample search queries
    queries = [
        "emails about project deadlines",
        "urgent server issues",
        "meeting requests"
    ]
    
    for query in queries:
        print(f"\nSearching for: '{query}'")
        results = ai_service.search_emails(query, n_results=2)
        
        if not results:
            print("  No results found.")
            continue
            
        for i, result in enumerate(results, 1):
            print(f"\n  {i}. {result.subject}")
            print(f"     From: {result.sender}")
            print(f"     Date: {result.date}")
            print(f"     Score: {result.score:.2f}")
            print(f"     Snippet: {result.snippet[:100]}...")


def main():
    """Main function to run the demo."""
    print_divider("Phoenix AI Features Demo")
    
    # Initialize AI service
    print("Initializing AI service...")
    ai_service = AIService()
    
    if not ai_service.available:
        print("\nERROR: AI features are not available. Please check your configuration.")
        print("Make sure you have set the OPENAI_API_KEY environment variable and installed all required dependencies.")
        return
    
    # Run demos
    demo_email_processing(ai_service)
    demo_semantic_search(ai_service)
    
    print_divider("Demo Complete")
    print("\nThank you for trying out the Phoenix AI features!")


if __name__ == "__main__":
    main()
