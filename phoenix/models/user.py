"""
User model for Project Phoenix.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .base import Base

class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    date_joined = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON, default=dict)
    
    # Relationships
    email_actions = relationship("EmailActionTaken", back_populates="user")
    behaviors = relationship("UserBehavior", back_populates="user")
    outlook_imports = relationship("OutlookImport", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def to_dict(self):
        """Convert user object to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'date_joined': self.date_joined.isoformat() if self.date_joined else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
