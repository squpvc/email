"""
Email models for Project Phoenix.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, Integer, 
    Table, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base


class EmailStatus(str, Enum):
    """Status of an email message."""
    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"
    ARCHIVED = "archived"
    TRASH = "trash"
    SPAM = "spam"


class EmailPriority(str, Enum):
    """Priority of an email message."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class Email(Base):
    """Email message model."""
    __tablename__ = "emails"
    
    # Message information
    message_id: Mapped[str] = Column(String(512), unique=True, index=True, nullable=False)
    in_reply_to: Mapped[Optional[str]] = Column(String(512), index=True)
    references: Mapped[Optional[str]] = Column(Text)
    
    # Sender and recipients
    from_address: Mapped[str] = Column(String(512), nullable=False)
    to_addresses: Mapped[List[str]] = Column(String, default=list)  # List of email addresses
    cc_addresses: Mapped[List[str]] = Column(String, default=list)
    bcc_addresses: Mapped[List[str]] = Column(String, default=list)
    
    # Content
    subject: Mapped[Optional[str]] = Column(Text)
    body_text: Mapped[Optional[str]] = Column(Text)
    body_html: Mapped[Optional[str]] = Column(Text)
    
    # Metadata
    status: Mapped[EmailStatus] = Column(SQLEnum(EmailStatus), default=EmailStatus.RECEIVED, index=True)
    priority: Mapped[EmailPriority] = Column(SQLEnum(EmailPriority), default=EmailPriority.NORMAL)
    read: Mapped[bool] = Column(Boolean, default=False, index=True)
    flagged: Mapped[bool] = Column(Boolean, default=False, index=True)
    
    # Dates
    sent_date: Mapped[Optional[datetime]] = Column(DateTime, index=True)
    received_date: Mapped[Optional[datetime]] = Column(DateTime, index=True)
    
    # Relationships
    account_id: Mapped[str] = Column(String(36), ForeignKey("email_accounts.id"), index=True)
    folder_id: Mapped[Optional[str]] = Column(String(36), ForeignKey("email_folders.id"), index=True)
    
    # Many-to-many relationship with labels through the EmailLabel model
    label_mappings: Mapped[List["EmailLabel"]] = relationship(
        "EmailLabel",
        back_populates="email",
        cascade="all, delete-orphan"
    )
    
    # Relationship to EmailCategoryMapping for category assignments
    category_mappings: Mapped[List["EmailCategoryMapping"]] = relationship(
        "EmailCategoryMapping",
        back_populates="email",
        cascade="all, delete-orphan",
        foreign_keys="[EmailCategoryMapping.email_id]"
    )
    
    # Property to access labels directly
    @property
    def labels(self) -> List["Label"]:
        return [mapping.label for mapping in self.label_mappings]
    
    # Property to access categories directly
    @property
    def categories(self) -> List["EmailCategory"]:
        return [mapping.category for mapping in self.category_mappings]
    
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment", 
        back_populates="email",
        cascade="all, delete-orphan"
    )
    
    # Full-text search index
    __table_args__ = (
        Index('ix_emails_fts', 'subject', 'body_text', postgresql_using='gin'),
    )


class EmailAccount(Base):
    """Email account model."""
    __tablename__ = "email_accounts"
    
    # Account information
    email: Mapped[str] = Column(String(512), unique=True, nullable=False, index=True)
    display_name: Mapped[Optional[str]] = Column(String(256))
    
    # Protocol settings (IMAP/SMTP)
    imap_server: Mapped[Optional[str]] = Column(String(256))
    imap_port: Mapped[Optional[int]] = Column(Integer)
    imap_ssl: Mapped[bool] = Column(Boolean, default=True)
    
    smtp_server: Mapped[Optional[str]] = Column(String(256))
    smtp_port: Mapped[Optional[int]] = Column(Integer)
    smtp_ssl: Mapped[bool] = Column(Boolean, default=True)
    
    # Authentication (encrypted)
    username: Mapped[Optional[str]] = Column(String(256))
    password: Mapped[Optional[str]] = Column(String(512))  # Will be encrypted
    oauth_token: Mapped[Optional[str]] = Column(Text)  # For OAuth2
    
    # Sync settings
    sync_enabled: Mapped[bool] = Column(Boolean, default=True)
    last_sync: Mapped[Optional[datetime]] = Column(DateTime)
    
    # Relationships
    folders: Mapped[List["EmailFolder"]] = relationship(
        "EmailFolder", 
        back_populates="account",
        cascade="all, delete-orphan"
    )
    emails: Mapped[List["Email"]] = relationship(
        "Email", 
        back_populates="account",
        cascade="all, delete-orphan"
    )


class EmailFolder(Base):
    """Email folder model."""
    __tablename__ = "email_folders"
    
    name: Mapped[str] = Column(String(256), nullable=False)
    full_name: Mapped[str] = Column(String(512), nullable=False, index=True)
    delimiter: Mapped[str] = Column(String(1), default="/")
    
    # Folder attributes
    no_select: Mapped[bool] = Column(Boolean, default=False)
    no_inferiors: Mapped[bool] = Column(Boolean, default=False)
    marked: Mapped[bool] = Column(Boolean, default=False)
    has_children: Mapped[bool] = Column(Boolean, default=False)
    
    # Special folder types
    is_inbox: Mapped[bool] = Column(Boolean, default=False, index=True)
    is_sent: Mapped[bool] = Column(Boolean, default=False, index=True)
    is_drafts: Mapped[bool] = Column(Boolean, default=False, index=True)
    is_trash: Mapped[bool] = Column(Boolean, default=False, index=True)
    is_spam: Mapped[bool] = Column(Boolean, default=False, index=True)
    is_archive: Mapped[bool] = Column(Boolean, default=False, index=True)
    
    # Relationships
    account_id: Mapped[str] = Column(
        String(36), 
        ForeignKey("email_accounts.id", ondelete="CASCADE"), 
        index=True
    )
    account: Mapped["EmailAccount"] = relationship("EmailAccount", back_populates="folders")
    emails: Mapped[List["Email"]] = relationship("Email", back_populates="folder")
    
    # For hierarchical folders
    parent_id: Mapped[Optional[str]] = Column(
        String(36), 
        ForeignKey("email_folders.id", ondelete="CASCADE"),
        index=True
    )
    children: Mapped[List["EmailFolder"]] = relationship(
        "EmailFolder",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    parent: Mapped[Optional["EmailFolder"]] = relationship(
        "EmailFolder", 
        remote_side=[id],
        back_populates="children"
    )


class Label(Base):
    """Label model for categorizing emails."""
    __tablename__ = "labels"
    
    name: Mapped[str] = Column(String(256), nullable=False, index=True)
    color: Mapped[Optional[str]] = Column(String(7))  # Hex color code
    
    # Relationships
    account_id: Mapped[str] = Column(
        String(36), 
        ForeignKey("email_accounts.id", ondelete="CASCADE"),
        index=True
    )
    account: Mapped["EmailAccount"] = relationship("EmailAccount")
    
    # Relationship through EmailLabel model
    email_mappings: Mapped[List["EmailLabel"]] = relationship(
        "EmailLabel",
        back_populates="label",
        cascade="all, delete-orphan"
    )
    
    # Property to access emails directly
    @property
    def emails(self) -> List["Email"]:
        return [mapping.email for mapping in self.email_mappings]


class Attachment(Base):
    """Email attachment model."""
    __tablename__ = "attachments"
    
    filename: Mapped[str] = Column(String(512), nullable=False)
    content_type: Mapped[str] = Column(String(256), default="application/octet-stream")
    content_disposition: Mapped[Optional[str]] = Column(String(64))
    content_id: Mapped[Optional[str]] = Column(String(512))
    size: Mapped[int] = Column(Integer, nullable=False)  # Size in bytes
    
    # File storage
    file_path: Mapped[Optional[str]] = Column(Text)  # Path to the file on disk
    content: Mapped[Optional[bytes]]  # For small attachments stored in DB
    
    # Relationships
    email_id: Mapped[str] = Column(
        String(36), 
        ForeignKey("emails.id", ondelete="CASCADE"),
        index=True
    )
    email: Mapped["Email"] = relationship("Email", back_populates="attachments")
