"""
Outlook Import Models.

This module defines the database models for Outlook PST/OST import functionality.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Float
from sqlalchemy.orm import relationship, backref

from .base import Base

class OutlookImport(Base):
    """
    Represents an Outlook PST/OST file import operation.
    """
    __tablename__ = 'outlook_imports'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    status = Column(String(20), default='pending', nullable=False)  # pending, analyzing, in_progress, completed, failed
    stats = Column(JSON, default=dict)  # Store import statistics
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship('User', back_populates='outlook_imports')
    mappings = relationship('OutlookImportMapping', back_populates='import_', cascade='all, delete-orphan')
    emails = relationship('Email', back_populates='outlook_import')
    
    def __repr__(self) -> str:
        return f"<OutlookImport(id={self.id}, file='{self.file_path}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the import record to a dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'status': self.status,
            'stats': self.stats or {},
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'mapping_count': len(self.mappings)
        }


class OutlookImportMapping(Base):
    """
    Maps Outlook folders to Phoenix categories/labels during import.
    """
    __tablename__ = 'outlook_import_mappings'
    
    id = Column(Integer, primary_key=True)
    import_id = Column(Integer, ForeignKey('outlook_imports.id', ondelete='CASCADE'), nullable=False)
    source_path = Column(String, nullable=False)  # Path in the PST/OST file (e.g., "Inbox/Subfolder")
    category_id = Column(Integer, ForeignKey('email_categories.id', ondelete='SET NULL'), nullable=True)
    label_id = Column(Integer, ForeignKey('email_labels.id', ondelete='SET NULL'), nullable=True)
    item_count = Column(Integer, default=0)  # Number of items imported with this mapping
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    import_ = relationship('OutlookImport', back_populates='mappings')
    category = relationship('EmailCategory')
    label = relationship('EmailLabel')
    
    def __repr__(self) -> str:
        return f"<OutlookImportMapping(id={self.id}, import_id={self.import_id}, source='{self.source_path}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the mapping to a dictionary."""
        return {
            'id': self.id,
            'import_id': self.import_id,
            'source_path': self.source_path,
            'category_id': self.category_id,
            'label_id': self.label_id,
            'item_count': self.item_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'category': self.category.to_dict() if self.category else None,
            'label': self.label.to_dict() if self.label else None
        }
