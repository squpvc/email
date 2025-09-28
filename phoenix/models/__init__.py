"""
Data models for Project Phoenix.

This package contains all the data models and schemas used throughout
the application for representing users, emails, events, tasks, and other entities.
"""

from .base import Base
from .user import User
from .email import (
    Email, 
    EmailAccount, 
    EmailFolder, 
    Label, 
    Attachment,
    EmailStatus,
    EmailPriority
)
from .calendar import (
    Event,
    Calendar,
    CalendarAccount,
    TaskAccount,
    TaskList,
    Task,
    EventStatus,
    EventVisibility,
    TaskStatus,
    TaskPriority
)
from .email_management import (
    EmailCategory,
    EmailLabel as EmailLabelMgmt,  # Alias to avoid conflict with email.Label
    EmailAction,
    EmailActionTaken,
    UserBehavior,
    OutlookImport,
    OutlookImportMapping
)

# Update Email model with relationships from email_management
from .email_management import update_email_model
update_email_model()

__all__ = [
    'Base',
    'User',
    'Email',
    'EmailAccount',
    'EmailFolder',
    'Label',
    'Attachment',
    'EmailStatus',
    'EmailPriority',
    'Event',
    'Calendar',
    'CalendarAccount',
    'TaskAccount',
    'TaskList',
    'Task',
    'EventStatus',
    'EventVisibility',
    'TaskStatus',
    'TaskPriority',
    'EmailCategory',
    'EmailLabelMgmt',
    'EmailAction',
    'EmailActionTaken',
    'UserBehavior',
    'OutlookImport',
    'OutlookImportMapping'
]
