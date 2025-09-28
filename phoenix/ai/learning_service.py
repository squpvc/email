"""
Learning service for tracking user actions and improving AI suggestions.

This module provides functionality to:
- Track user actions on emails
- Learn from user feedback
- Improve AI suggestions over time
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from joblib import dump, load
import os

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.email_management import (
    Email, EmailCategory, EmailLabel, EmailAction, 
    EmailCategoryMapping, UserBehavior, EmailActionTaken
)
from ..config import DATA_DIR

logger = logging.getLogger(__name__)

class LearningService:
    """Service for learning from user actions."""
    
    def __init__(self, db_session: Session):
        """Initialize the learning service."""
        self.db = db_session
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.category_model = None
        self.action_model = None
        self._init_models()
    
    def _init_models(self) -> None:
        """Initialize or load the ML models."""
        os.makedirs(DATA_DIR / 'models', exist_ok=True)
        self.category_model_path = DATA_DIR / 'models' / 'category_model.joblib'
        self.action_model_path = DATA_DIR / 'models' / 'action_model.joblib'
        self.vectorizer_path = DATA_DIR / 'models' / 'vectorizer.joblib'
        
        try:
            if self.category_model_path.exists():
                self.category_model = load(self.category_model_path)
            else:
                self.category_model = SGDClassifier(loss='log_loss')
            
            if self.action_model_path.exists():
                self.action_model = load(self.action_model_path)
            else:
                self.action_model = SGDClassifier(loss='log_loss')
                
            if self.vectorizer_path.exists():
                self.vectorizer = load(self.vectorizer_path)
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.category_model = SGDClassifier(loss='log_loss')
            self.action_model = SGDClassifier(loss='log_loss')
    
    def save_models(self) -> None:
        """Save the trained models to disk."""
        try:
            if self.category_model:
                dump(self.category_model, self.category_model_path)
            if self.action_model:
                dump(self.action_model, self.action_model_path)
            if self.vectorizer:
                dump(self.vectorizer, self.vectorizer_path)
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def log_action(
        self,
        email: Email,
        action_name: str,
        action_params: Optional[Dict[str, Any]] = None,
        corrected_category_id: Optional[int] = None,
        corrected_label_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> None:
        """
        Log a user action for learning.
        
        Args:
            email: The email the action was taken on
            action_name: Name of the action (e.g., 'reply', 'forward', 'categorize')
            action_params: Parameters of the action
            corrected_category_id: The correct category if the user corrected an AI suggestion
            corrected_label_id: The correct label if the user corrected an AI suggestion
            user_id: ID of the user who performed the action
        """
        try:
            # Create behavior pattern from email
            pattern = self._create_behavior_pattern(email)
            
            # Check if similar behavior already exists
            existing = self.db.query(UserBehavior).filter(
                UserBehavior.behavior_type == 'email_processing',
                UserBehavior.pattern['sender'].astext == pattern.get('sender', ''),
                UserBehavior.pattern['subject_keywords'].astext == json.dumps(pattern.get('subject_keywords', [])),
                UserBehavior.action == action_name
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
                    action=action_name,
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
                        is_user_confirmed=True,
                        confidence=1.0
                    )
                    self.db.add(mapping)
                else:
                    mapping.is_user_confirmed = True
                    mapping.confidence = 1.0
                    if corrected_label_id is not None:
                        mapping.label_id = corrected_label_id
            
            # Log the action
            action_taken = EmailActionTaken(
                email_id=email.id,
                action_name=action_name,
                parameters=action_params or {},
                user_id=user_id,
                timestamp=datetime.utcnow()
            )
            self.db.add(action_taken)
            
            self.db.commit()
            
            # Retrain models periodically based on new data
            self._retrain_models()
            
        except Exception as e:
            logger.error(f"Error logging action: {e}")
            self.db.rollback()
    
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
            'word_count': len((email.body_plain or '').split())
        }
    
    def _retrain_models(self) -> None:
        """Retrain the ML models with new data."""
        try:
            # Only retrain periodically (e.g., every 100 new actions)
            action_count = self.db.query(func.count(EmailActionTaken.id)).scalar()
            if action_count % 100 != 0:
                return
                
            logger.info("Retraining AI models with new data...")
            
            # Get training data for category model
            category_data = self._get_category_training_data()
            if category_data and len(category_data['X']) > 10:  # Minimum samples
                X = self.vectorizer.fit_transform(category_data['X'])
                self.category_model.partial_fit(
                    X, category_data['y'],
                    classes=category_data['classes']
                )
            
            # Get training data for action model
            action_data = self._get_action_training_data()
            if action_data and len(action_data['X']) > 10:  # Minimum samples
                X = self.vectorizer.transform(action_data['X'])
                self.action_model.partial_fit(
                    X, action_data['y'],
                    classes=action_data['classes']
                )
            
            # Save the updated models
            self.save_models()
            
        except Exception as e:
            logger.error(f"Error retraining models: {e}")
    
    def _get_category_training_data(self) -> Dict[str, Any]:
        """Get training data for the category model."""
        # Get confirmed category mappings
        mappings = self.db.query(
            EmailCategoryMapping,
            Email
        ).join(
            Email, Email.id == EmailCategoryMapping.email_id
        ).filter(
            EmailCategoryMapping.is_user_confirmed == True
        ).limit(1000).all()  # Limit to prevent memory issues
        
        if not mappings:
            return {}
        
        # Prepare training data
        X = []
        y = []
        
        for mapping, email in mappings:
            # Create feature vector from email
            features = self._extract_features(email)
            X.append(features)
            y.append(str(mapping.category_id))
        
        return {
            'X': X,
            'y': y,
            'classes': list(set(y))
        }
    
    def _get_action_training_data(self) -> Dict[str, Any]:
        """Get training data for the action model."""
        # Get recent actions
        actions = self.db.query(
            EmailActionTaken,
            Email
        ).join(
            Email, Email.id == EmailActionTaken.email_id
        ).order_by(
            EmailActionTaken.timestamp.desc()
        ).limit(1000).all()  # Limit to prevent memory issues
        
        if not actions:
            return {}
        
        # Prepare training data
        X = []
        y = []
        
        for action, email in actions:
            # Create feature vector from email
            features = self._extract_features(email)
            X.append(features)
            y.append(action.action_name)
        
        return {
            'X': X,
            'y': y,
            'classes': list(set(y))
        }
    
    def _extract_features(self, email: Email) -> str:
        """Extract features from an email for ML models."""
        features = []
        
        # Subject
        if email.subject:
            features.append(email.subject)
        
        # Sender domain
        if email.sender_email and '@' in email.sender_email:
            features.append(f"FROM_DOMAIN:{email.sender_email.split('@')[-1]}")
        
        # Body text (first 100 chars)
        if email.body_plain:
            features.append(email.body_plain[:100])
        
        # Has attachments
        if email.attachments:
            features.append("HAS_ATTACHMENTS")
        
        return " ".join(features)
    
    def predict_category(self, email: Email) -> List[Dict[str, Any]]:
        """Predict categories for an email."""
        if not self.category_model or not hasattr(self.category_model, 'classes_'):
            return []
        
        try:
            # Extract features
            features = self._extract_features(email)
            X = self.vectorizer.transform([features])
            
            # Get predictions
            probabilities = self.category_model.predict_proba(X)[0]
            
            # Map to category IDs and confidence scores
            results = []
            for i, prob in enumerate(probabilities):
                if prob > 0.1:  # Minimum confidence threshold
                    category_id = int(self.category_model.classes_[i])
                    results.append({
                        'category_id': category_id,
                        'confidence': float(prob)
                    })
            
            # Sort by confidence (highest first)
            results.sort(key=lambda x: x['confidence'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Error predicting category: {e}")
            return []
    
    def predict_actions(self, email: Email) -> List[Dict[str, Any]]:
        """Predict actions for an email."""
        if not self.action_model or not hasattr(self.action_model, 'classes_'):
            return []
        
        try:
            # Extract features
            features = self._extract_features(email)
            X = self.vectorizer.transform([features])
            
            # Get predictions
            probabilities = self.action_model.predict_proba(X)[0]
            
            # Map to action names and confidence scores
            results = []
            for i, prob in enumerate(probabilities):
                if prob > 0.1:  # Minimum confidence threshold
                    action_name = self.action_model.classes_[i]
                    results.append({
                        'action_name': action_name,
                        'confidence': float(prob)
                    })
            
            # Sort by confidence (highest first)
            results.sort(key=lambda x: x['confidence'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Error predicting actions: {e}")
            return []


def get_learning_service(db_session: Session) -> LearningService:
    """Get an instance of the learning service."""
    return LearningService(db_session)
