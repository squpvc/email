"""
Calendar and task models for Project Phoenix.
"""
from datetime import datetime, time
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, Integer, 
    JSON, Enum as SQLEnum, Table, Date, Time, Index
)
from sqlalchemy.orm import relationship, Mapped

from .base import Base


class EventStatus(str, Enum):
    """Status of a calendar event."""
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class EventVisibility(str, Enum):
    """Visibility of a calendar event."""
    DEFAULT = "default"
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class EventReminderMethod(str, Enum):
    """Reminder methods for calendar events."""
    DISPLAY = "display"
    EMAIL = "email"
    SOUND = "sound"


class Calendar(Base):
    """Calendar model."""
    __tablename__ = "calendars"
    
    name: Mapped[str] = Column(String(256), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    color: Mapped[str] = Column(String(7), default="#3a87ad")  # Hex color code
    
    # Timezone information
    timezone: Mapped[str] = Column(String(64), default="UTC")
    
    # Sync information
    is_primary: Mapped[bool] = Column(Boolean, default=False, index=True)
    is_shared: Mapped[bool] = Column(Boolean, default=False)
    is_read_only: Mapped[bool] = Column(Boolean, default=False)
    
    # External calendar integration
    external_id: Mapped[Optional[str]] = Column(String(512), index=True)
    external_url: Mapped[Optional[str]] = Column(Text)
    
    # Relationships
    account_id: Mapped[Optional[str]] = Column(
        String(36), 
        ForeignKey("calendar_accounts.id", ondelete="CASCADE"),
        index=True
    )
    account: Mapped["CalendarAccount"] = relationship("CalendarAccount", back_populates="calendars")
    events: Mapped[List["Event"]] = relationship(
        "Event", 
        back_populates="calendar",
        cascade="all, delete-orphan"
    )


class Event(Base):
    """Calendar event model."""
    __tablename__ = "events"
    
    # Basic information
    title: Mapped[str] = Column(String(512), nullable=False, index=True)
    description: Mapped[Optional[str]] = Column(Text)
    location: Mapped[Optional[str]] = Column(Text)
    
    # Time information
    start: Mapped[datetime] = Column(DateTime, nullable=False, index=True)
    end: Mapped[datetime] = Column(DateTime, nullable=False, index=True)
    all_day: Mapped[bool] = Column(Boolean, default=False, index=True)
    timezone: Mapped[Optional[str]] = Column(String(64))
    
    # Recurrence
    is_recurring: Mapped[bool] = Column(Boolean, default=False, index=True)
    recurrence_rule: Mapped[Optional[str]] = Column(Text)  # iCalendar RRULE format
    recurrence_id: Mapped[Optional[str]] = Column(String(512), index=True)
    
    # Status and visibility
    status: Mapped[EventStatus] = Column(
        SQLEnum(EventStatus), 
        default=EventStatus.CONFIRMED, 
        index=True
    )
    visibility: Mapped[EventVisibility] = Column(
        SQLEnum(EventVisibility), 
        default=EventVisibility.DEFAULT
    )
    
    # Organizer and attendees
    organizer: Mapped[Optional[str]] = Column(String(512))  # Email address
    attendees: Mapped[List[dict]] = Column(JSON, default=list)  # List of {email, name, status, role}
    
    # Reminders
    reminders: Mapped[List[dict]] = Column(JSON, default=list)  # List of {minutes, method}
    
    # External data
    external_id: Mapped[Optional[str]] = Column(String(512), index=True)
    external_url: Mapped[Optional[str]] = Column(Text)
    
    # Relationships
    calendar_id: Mapped[str] = Column(
        String(36), 
        ForeignKey("calendars.id", ondelete="CASCADE"),
        index=True
    )
    calendar: Mapped["Calendar"] = relationship("Calendar", back_populates="events")
    
    # Full-text search index
    __table_args__ = (
        Index('ix_events_fts', 'title', 'description', 'location', postgresql_using='gin'),
    )


class TaskStatus(str, Enum):
    """Status of a task."""
    NEEDS_ACTION = "needs_action"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority of a task."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TaskList(Base):
    """Task list model."""
    __tablename__ = "task_lists"
    
    name: Mapped[str] = Column(String(256), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    color: Mapped[str] = Column(String(7), default="#468847")  # Hex color code
    
    # Access control
    is_shared: Mapped[bool] = Column(Boolean, default=False)
    is_editable: Mapped[bool] = Column(Boolean, default=True)
    
    # External task list integration
    external_id: Mapped[Optional[str]] = Column(String(512), index=True)
    external_url: Mapped[Optional[str]] = Column(Text)
    
    # Relationships
    account_id: Mapped[Optional[str]] = Column(
        String(36), 
        ForeignKey("task_accounts.id", ondelete="CASCADE"),
        index=True
    )
    account: Mapped["TaskAccount"] = relationship("TaskAccount", back_populates="task_lists")
    tasks: Mapped[List["Task"]] = relationship(
        "Task", 
        back_populates="task_list",
        cascade="all, delete-orphan"
    )


class Task(Base):
    """Task model."""
    __tablename__ = "tasks"
    
    # Basic information
    title: Mapped[str] = Column(String(512), nullable=False, index=True)
    description: Mapped[Optional[str]] = Column(Text)
    
    # Status and priority
    status: Mapped[TaskStatus] = Column(
        SQLEnum(TaskStatus), 
        default=TaskStatus.NEEDS_ACTION, 
        index=True
    )
    priority: Mapped[TaskPriority] = Column(
        SQLEnum(TaskPriority), 
        default=TaskPriority.NORMAL,
        index=True
    )
    
    # Dates
    due_date: Mapped[Optional[Date]] = Column(Date, index=True)
    due_time: Mapped[Optional[Time]] = Column(Time)
    completed_at: Mapped[Optional[DateTime]] = Column(DateTime, index=True)
    
    # Progress tracking
    percent_complete: Mapped[int] = Column(Integer, default=0)  # 0-100
    
    # Recurrence
    is_recurring: Mapped[bool] = Column(Boolean, default=False, index=True)
    recurrence_rule: Mapped[Optional[str]] = Column(Text)  # iCalendar RRULE format
    
    # Reminders
    reminder_datetime: Mapped[Optional[DateTime]] = Column(DateTime, index=True)
    
    # External data
    external_id: Mapped[Optional[str]] = Column(String(512), index=True)
    external_url: Mapped[Optional[str]] = Column(Text)
    
    # Relationships
    task_list_id: Mapped[str] = Column(
        String(36), 
        ForeignKey("task_lists.id", ondelete="CASCADE"),
        index=True
    )
    task_list: Mapped["TaskList"] = relationship("TaskList", back_populates="tasks")
    
    # Parent-child relationship for subtasks
    parent_id: Mapped[Optional[str]] = Column(
        String(36), 
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True
    )
    parent: Mapped[Optional["Task"]] = relationship(
        "Task", 
        remote_side=[id],
        back_populates="subtasks"
    )
    subtasks: Mapped[List["Task"]] = relationship(
        "Task", 
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    # Full-text search index
    __table_args__ = (
        Index('ix_tasks_fts', 'title', 'description', postgresql_using='gin'),
    )


class CalendarAccount(Base):
    """Calendar account model."""
    __tablename__ = "calendar_accounts"
    
    # Account information
    name: Mapped[str] = Column(String(256), nullable=False)
    email: Mapped[str] = Column(String(512), index=True)
    
    # Protocol settings (CalDAV)
    server_url: Mapped[Optional[str]] = Column(Text)
    username: Mapped[Optional[str]] = Column(String(256))
    password: Mapped[Optional[str]] = Column(String(512))  # Will be encrypted
    
    # Sync settings
    sync_enabled: Mapped[bool] = Column(Boolean, default=True)
    last_sync: Mapped[Optional[DateTime]] = Column(DateTime)
    
    # Relationships
    calendars: Mapped[List["Calendar"]] = relationship(
        "Calendar", 
        back_populates="account",
        cascade="all, delete-orphan"
    )


class TaskAccount(Base):
    """Task account model."""
    __tablename__ = "task_accounts"
    
    # Account information
    name: Mapped[str] = Column(String(256), nullable=False)
    email: Mapped[Optional[str]] = Column(String(512), index=True)
    
    # Protocol settings (CalDAV for tasks)
    server_url: Mapped[Optional[str]] = Column(Text)
    username: Mapped[Optional[str]] = Column(String(256))
    password: Mapped[Optional[str]] = Column(String(512))  # Will be encrypted
    
    # Sync settings
    sync_enabled: Mapped[bool] = Column(Boolean, default=True)
    last_sync: Mapped[Optional[DateTime]] = Column(DateTime)
    
    # Relationships
    task_lists: Mapped[List["TaskList"]] = relationship(
        "TaskList", 
        back_populates="account",
        cascade="all, delete-orphan"
    )
