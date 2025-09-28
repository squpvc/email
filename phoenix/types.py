"""
Type definitions and interfaces for Project Phoenix.
"""
from typing import Optional, Dict, Any, Type, Callable, TYPE_CHECKING
from PyQt6.QtWidgets import QApplication

# Import the base application interface
from .application_base import PhoenixApplicationBase

# For type checking, import the actual application class
if TYPE_CHECKING:
    from .application import PhoenixApplication
