"""
Base database models for Project Phoenix.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped


@as_declarative()
class Base:
    """Base class for all database models."""
    
    id: Mapped[str] = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid4()),
        index=True
    )
    created_at: Mapped[datetime] = Column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate __tablename__ automatically.
        
        Converts CamelCase class name to snake_case table name.
        
        Returns:
            str: The table name in snake_case
        """
        return ''.join(
            ['_' + i.lower() if i.isupper() else i 
             for i in cls.__name__]
        ).lstrip('_')

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary.
        
        Returns:
            dict: A dictionary containing all column names and their values
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
