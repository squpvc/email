"""
AI-powered email processing service.

This module provides functionality for:
- Categorizing emails using AI
- Suggesting actions based on email content
- Learning from user behavior
- Finding related emails
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from sqlalchemy.orm import Session
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..models.email_management import (
    Email, EmailCategory, EmailLabel, EmailAction, 
    EmailCategoryMapping, UserBehavior
)
from ..config import config

logger = logging.getLogger(__name__)

class EmailProcessor:
    """AI-powered email processing service."""
    
    def __init__(self, db_session: Session):
        """Initialize the email processor."""
        self.db = db_session
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.category_model = None
        self.action_model = None
        self._init_models()
    
    def _init_models(self):
        """Initialize AI models for email processing."""
        # TODO: Load or train models
        # For now, we'll use simple keyword matching
        self._init_keyword_matching()
    
    def _init_keyword_matching(self):
        """Initialize simple keyword matching for categories and actions."""
        # Simple keyword-based matching as fallback
        self.category_keywords = {
            'work': ['meeting', 'report', 'deadline', 'project', 'team'],
            'personal': ['family', 'friend', 'personal', 'hello', 'hi'],
            'finance': ['invoice', 'bill', 'payment', 'bank', 'statement'],
            'shopping': ['order', 'purchase', 'delivery', 'shipping', 'tracking'],
            'travel': ['flight', 'hotel', 'booking', 'itinerary', 'trip']
        }
        
        self.action_keywords = {
            'reply': ['question', 'let me know', 'get back to me', 'your thoughts'],
            'schedule_meeting': ['meeting', 'call', 'discuss', 'schedule', 'calendar'],
            'create_task': ['todo', 'task', 'action item', 'follow up', 'remind me'],
            'forward': ['FYI', 'for your information', 'please review', 'take a look'],
            'delete': ['unsubscribe', 'notification', 'newsletter', 'promotion']
        }
    
    async def categorize_email(self, email: Email) -> List[Dict[str, Any]]:
        """
        Categorize an email and return suggested categories with confidence scores.
        
        Args:
            email: The email to categorize
            
        Returns:
            List of dicts with category_id, label_id, and confidence
        """
        # Get existing categories from the database
        categories = self.db.query(EmailCategory).all()
        
        if not categories:
            logger.warning("No categories found in the database")
            return []
        
        # Prepare email text for analysis
        email_text = self._prepare_email_text(email)
        
        # Get AI predictions (simple keyword matching for now)
        predictions = []
        
        for category in categories:
            # Check for keyword matches
            confidence = self._get_keyword_confidence(
                email_text, 
                self.category_keywords.get(category.name.lower(), [])
            )
            
            if confidence > 0:
                predictions.append({
                    'category_id': category.id,
                    'label_id': None,  # Will be determined later
                    'confidence': min(confidence * 0.8, 0.95)  # Cap confidence for keyword matching
                })
        
        # If no categories matched with sufficient confidence, use "Other"
        if not predictions or max(p.get('confidence', 0) for p in predictions) < 0.3:
            other_category = self.db.query(EmailCategory).filter_by(name='Other').first()
            if other_category:
                predictions.append({
                    'category_id': other_category.id,
                    'label_id': None,
                    'confidence': 0.9  # High confidence for "Other" when nothing else matches
                })
        
        # Sort by confidence (highest first)
        predictions.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Limit to top 3 predictions
        return predictions[:3]
    
    async def suggest_actions(self, email: Email) -> List[Dict[str, Any]]:
        """
        Suggest actions for an email.
        
        Args:
            email: The email to suggest actions for
            
        Returns:
            List of dicts with action_id and confidence
        """
        # Get existing actions from the database
        actions = self.db.query(EmailAction).all()
        
        if not actions:
            logger.warning("No actions found in the database")
            return []
        
        # Prepare email text for analysis
        email_text = self._prepare_email_text(email)
        
        # Get AI predictions (simple keyword matching for now)
        suggestions = []
        
        for action in actions:
            # Check for keyword matches
            confidence = self._get_keyword_confidence(
                email_text,
        self, 
        email: Email, 
        limit: int = 10,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Find emails related to the given email."""
        if not email:
        # Get recent emails from the same sender or with similar subjects
        time_threshold = datetime.utcnow() - timedelta(days=30)
        
        query = self.db.query(Email).filter(
            Email.id != email.id,
            Email.received_at >= time_threshold
        )
        
        # If we have a sender, prioritize emails from the same sender
        if email.sender_email:
            query = query.filter(
                (Email.sender_email == email.sender_email) |
                (Email.subject.ilike(f"%{email.subject[:30]}%"))
            )
        else:
            query = query.filter(Email.subject.ilike(f"%{email.subject[:30]}%"))
        
        recent_emails = query.order_by(Email.received_at.desc()).limit(50).all()
        
        if not recent_emails:
            return []
        
        # Prepare texts for similarity comparison
        target_text = self._prepare_email_text(email)
        texts = [target_text] + [self._prepare_email_text(e) for e in recent_emails]
        
        # Calculate TF-IDF vectors
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        except Exception as e:
            logger.error(f"Error calculating email similarities: {e}")
            return []
        
        # Get top similar emails
        related_emails = []
        for i, similarity in enumerate(similarities):
            if similarity >= min_similarity:
                related_emails.append({
                    'email_id': recent_emails[i].id,
                    'similarity': float(similarity),
                    'email': recent_emails[i]
                })
        
        # Sort by similarity (highest first)
        related_emails.sort(key=lambda x: x['similarity'], reverse=True)
        
        return related_emails[:limit]
    
    async def learn_from_feedback(
        self,
        email: Email,
        action_taken: str,
        action_params: Optional[Dict[str, Any]] = None,
        corrected_category_id: Optional[int] = None,
        corrected_label_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> None:
        """
        Learn from user feedback to improve future predictions.
        
        Args:
            email: The email the feedback is for
            action_taken: The action taken by the user
            action_params: Parameters for the action
            corrected_category_id: The correct category ID if the user corrected it
            corrected_label_id: The correct label ID if the user corrected it
            user_id: ID of the user who provided the feedback
        """
        # Create behavior pattern from email
        pattern = self._create_behavior_pattern(email)
        
        # Check if similar behavior already exists
        existing = self.db.query(UserBehavior).filter(
            UserBehavior.behavior_type == 'email_processing',
            UserBehavior.pattern['sender'].astext == pattern.get('sender', ''),
            UserBehavior.pattern['subject_keywords'].astext == json.dumps(pattern.get('subject_keywords', [])),
            UserBehavior.action == action_taken
        ).first()
        
        if existing:
            # Update existing behavior
            existing.count += 1
            existing.last_used = datetime.utcnow()
            if action_params:
                existing.action_parameters = action_params
        else:
            # Create new behavior
            behavior = UserBehavior(
                user_id=user_id,
                behavior_type='email_processing',
                pattern=pattern,
                action=action_taken,
                action_parameters=action_params,
                count=1,
                last_used=datetime.utcnow()
            )
            self.db.add(behavior)
        
        # Handle category/label corrections
        if corrected_category_id is not None:
            # Update the email's category mapping
            mapping = self.db.query(EmailCategoryMapping).filter_by(
                email_id=email.id,
                category_id=corrected_category_id
            ).first()
            
            if not mapping:
                mapping = EmailCategoryMapping(
                    email_id=email.id,
                    category_id=corrected_category_id,
                    label_id=corrected_label_id,
                    is_user_confirmed=True
                )
                self.db.add(mapping)
            else:
                mapping.is_user_confirmed = True
                if corrected_label_id is not None:
                    mapping.label_id = corrected_label_id
        
        self.db.commit()
    
    def _prepare_email_text(self, email: Email) -> str:
        """Prepare email text for analysis."""
        text_parts = []
        
        if email.subject:
            text_parts.append(email.subject)
        
        if email.body_plain:
            text_parts.append(email.body_plain)
        
        if email.body_html:
            # TODO: Extract text from HTML
            pass
        
        return " ".join(part for part in text_parts if part)
    
    def _get_keyword_confidence(self, text: str, keywords: List[str]) -> float:
        """Calculate confidence based on keyword matches."""
        if not text or not keywords:
            return 0.0
        
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        
        # Calculate confidence based on the ratio of matched keywords to total keywords
        if not keywords:
            return 0.0
            
        confidence = matches / len(keywords)
        
        # Apply a sigmoid function to make the confidence more nuanced
        # This makes the confidence grow faster when there are few matches
        # and slower when approaching 1.0
        return 1 / (1 + np.exp(-10 * (confidence - 0.3)))
    
    def _create_behavior_pattern(self, email: Email) -> Dict[str, Any]:
        """Create a behavior pattern from an email."""
        # Extract keywords from subject
        subject_keywords = []
        if email.subject:
            # Simple keyword extraction - in a real implementation, use NLP
            words = email.subject.lower().split()
            # Filter out common words and keep only meaningful ones
            stop_words = {'the', 'and', 'or', 'a', 'an', 'in', 'on', 'at', 'to', 'for'}
            subject_keywords = [w for w in words if len(w) > 3 and w not in stop_words][:5]
        
        # Extract sender domain
        sender_domain = ""
        if email.sender_email and '@' in email.sender_email:
            sender_domain = email.sender_email.split('@')[-1]
        
        return {
            'sender': email.sender_email or '',
            'sender_domain': sender_domain,
            'subject_keywords': subject_keywords,
            'has_attachments': bool(email.attachments),
            'word_count': len(self._prepare_email_text(email).split())
        }


# Helper functions for working with the email processor
def get_email_processor(db_session: Session) -> EmailProcessor:
    """Get an instance of the email processor."""
    return EmailProcessor(db_session)


async def process_email(email: Email, db_session: Session) -> Dict[str, Any]:
    """Process an email and return categorization and action suggestions."""
    processor = get_email_processor(db_session)
    
    # Get category predictions
    categories = await processor.categorize_email(email)
    
    # Get action suggestions
    actions = await processor.suggest_actions(email)
    
    # Find related emails
    related_emails = await processor.find_related_emails(email)
    
    return {
        'categories': categories,
        'suggested_actions': actions,
        'related_emails': related_emails
    }
