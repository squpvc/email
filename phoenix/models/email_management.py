"""
Models for smart email management features.

This module contains SQLAlchemy models for:
- Email categories and labels
- Email actions and action history
- User behavior tracking
- Outlook import functionality
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, 
    Index, JSON, func, UniqueConstraint, text
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr
from .base import Base

class EmailCategory(Base):
    """Categories for organizing emails (e.g., Work, Personal, Finance)."""
    __tablename__ = 'email_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=False, default='#808080')  # Default gray
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    labels = relationship("EmailLabel", back_populates="category", cascade="all, delete-orphan")
    email_mappings = relationship("EmailCategoryMapping", back_populates="category")
    
    def __repr__(self):
        return f"<EmailCategory(id={self.id}, name='{self.name}')>"


class EmailLabel(Base):
    """Sub-categories or tags for more specific email organization."""
    __tablename__ = 'email_labels'
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('email_categories.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Inherit from category if None
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    category = relationship(
        "EmailCategory", 
        back_populates="labels",
        primaryjoin="EmailLabel.category_id == EmailCategory.id"
    )
    email_mappings = relationship(
        "EmailCategoryMapping", 
        back_populates="label",
        primaryjoin="EmailLabel.id == EmailCategoryMapping.label_id"
    )
    
    __table_args__ = (
        Index('idx_email_label_category_name', 'category_id', 'name', unique=True),
    )
    
    def __repr__(self):
        return f"<EmailLabel(id={self.id}, name='{self.name}', category_id={self.category_id})>"


class EmailAction(Base):
    """Available actions that can be taken on emails."""
    __tablename__ = 'email_actions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    is_system = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    actions_taken = relationship("EmailActionTaken", back_populates="action")
    
    def __repr__(self):
        return f"<EmailAction(id={self.id}, name='{self.name}')>"


# Define the mapping table explicitly to control the creation order
from sqlalchemy import Table, MetaData

# This needs to be defined before the EmailCategoryMapping class
email_category_mapping_table = Table(
    'email_category_mapping',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('email_id', Integer, ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('category_id', Integer, ForeignKey('email_categories.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('label_id', Integer, ForeignKey('email_labels.id', ondelete='SET NULL'), nullable=True, index=True),
    Column('confidence', Float, nullable=True),
    Column('is_user_confirmed', Boolean, nullable=True),
    Column('created_at', DateTime, server_default=func.now()),
    Column('updated_at', DateTime, server_default=func.now(), onupdate=func.now()),
    
    # Add constraints
    Index('idx_email_category_unique', 'email_id', 'category_id', unique=True),
    Index('idx_email_category_label_unique', 'email_id', 'category_id', 'label_id', 
          unique=True, sqlite_where=text('label_id IS NOT NULL')),
    
    # Ensure the table is created after email_labels
    info={'create_after': ['email_labels']}
)

class EmailCategoryMapping(Base):
    """Mapping between emails and their categories/labels.
    
    This table creates a many-to-many relationship between emails and categories,
    with an optional label for more specific categorization.
    """
    __table__ = email_category_mapping_table
    
    # Relationships
    email = relationship("Email", back_populates="category_mappings")
    category = relationship(
        "EmailCategory", 
        back_populates="email_mappings",
        primaryjoin="EmailCategoryMapping.category_id == EmailCategory.id"
    )
    label = relationship(
        "EmailLabel", 
        back_populates="email_mappings",
        primaryjoin="EmailCategoryMapping.label_id == EmailLabel.id"
    )
    
    def __repr__(self):
        return f"<EmailCategoryMapping(email_id={self.email_id}, category_id={self.category_id}, label_id={self.label_id})>"


class EmailActionTaken(Base):
    """Record of actions taken on emails."""
    __tablename__ = 'email_actions_taken'
    
    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey('emails.id', ondelete='CASCADE'), nullable=False)
    action_id = Column(Integer, ForeignKey('email_actions.id', ondelete='CASCADE'), nullable=False)
    parameters = Column(JSON, nullable=True)  # Store action-specific parameters
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    email = relationship("Email", back_populates="actions_taken")
    action = relationship("EmailAction", back_populates="actions_taken")
    user = relationship("User", back_populates="email_actions")
    
    __table_args__ = (
        Index('idx_email_actions_taken_email', 'email_id'),
        Index('idx_email_actions_taken_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<EmailActionTaken(id={self.id}, email_id={self.email_id}, action_id={self.action_id})>"


class UserBehavior(Base):
    """Track user behavior for learning patterns."""
    __tablename__ = 'user_behavior'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    behavior_type = Column(String(50), nullable=False)  # 'category', 'action', 'label', etc.
    pattern = Column(JSON, nullable=False)  # JSON pattern that triggered the behavior
    action = Column(String(100), nullable=False)  # The action taken
    action_parameters = Column(JSON, nullable=True)  # Parameters for the action
    count = Column(Integer, nullable=False, default=1)
    last_used = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="behaviors")
    
    __table_args__ = (
        Index('idx_user_behavior_type', 'behavior_type'),
        Index('idx_user_behavior_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<UserBehavior(id={self.id}, behavior_type='{self.behavior_type}', action='{self.action}')>"


class OutlookImport(Base):
    """Track Outlook PST/OST file imports."""
    __tablename__ = 'outlook_imports'
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    imported_at = Column(DateTime, server_default=func.now())
    status = Column(String(20), nullable=False, default='pending')  # pending, in_progress, completed, failed
    stats = Column(JSON, nullable=True)  # Store import statistics
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="outlook_imports")
    folder_mappings = relationship("OutlookImportMapping", back_populates="import_job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OutlookImport(id={self.id}, file_path='{self.file_path}', status='{self.status}')>"


class OutlookImportMapping(Base):
    """Mapping between Outlook folders and Phoenix categories/labels."""
    __tablename__ = 'outlook_import_mapping'
    
    id = Column(Integer, primary_key=True)
    import_id = Column(Integer, ForeignKey('outlook_imports.id', ondelete='CASCADE'), nullable=False)
    outlook_folder = Column(String(500), nullable=False)
    category_id = Column(Integer, ForeignKey('email_categories.id', ondelete='SET NULL'), nullable=True)
    label_id = Column(Integer, ForeignKey('email_labels.id', ondelete='SET NULL'), nullable=True)
    item_count = Column(Integer, nullable=False, default=0)
    
    # Relationships
    import_job = relationship("OutlookImport", back_populates="folder_mappings")
    category = relationship("EmailCategory")
    label = relationship("EmailLabel")
    
    __table_args__ = (
        Index('idx_outlook_import_mapping_import', 'import_id'),
    )
    
    def __repr__(self):
        return f"<OutlookImportMapping(id={self.id}, import_id={self.import_id}, outlook_folder='{self.outlook_folder}')>"


# Update the Email model to include relationships to the new models
def update_email_model():
    """Add relationships to the Email model."""
    from .email import Email
    
    # Add relationships to Email model
    Email.category_mappings = relationship(
        "EmailCategoryMapping", 
        back_populates="email",
        cascade="all, delete-orphan"
    )
    
    Email.actions_taken = relationship(
        "EmailActionTaken", 
        back_populates="email",
        cascade="all, delete-orphan"
    )
    
    # Add helper methods
    def get_categories(self, only_confirmed: bool = False):
        """Get categories for this email."""
        query = [m.category for m in self.category_mappings]
        if only_confirmed:
            query = [m.category for m in self.category_mappings 
                    if m.is_user_confirmed is True]
        return list(set(query))  # Ensure uniqueness
    
    Email.get_categories = get_categories
    
    def get_labels(self, only_confirmed: bool = False):
        """Get labels for this email."""
        query = [m.label for m in self.category_mappings if m.label is not None]
        if only_confirmed:
            query = [m.label for m in self.category_mappings 
                    if m.label is not None and m.is_user_confirmed is True]
        return list(set(query))  # Ensure uniqueness
    
    Email.get_labels = get_labels
    
    def get_actions(self):
        """Get actions taken on this email."""
        return [at.action for at in self.actions_taken]
    
    Email.get_actions = get_actions
