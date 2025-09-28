"""
Theme management for Project Phoenix.
"""
from typing import Dict, Any, Optional, Union

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication, QWidget, QStyleFactory, QStyle


def apply_theme(app_or_widget: Union[QApplication, QWidget], theme_name: str = "light") -> None:
    """Apply a theme to the application or widget.
    
    Args:
        app_or_widget: The QApplication or QWidget to apply the theme to
        theme_name: Name of the theme to apply ("light" or "dark")
    """
    theme = THEMES.get(theme_name.lower(), THEMES["light"])
    
    # Apply style
    style = QStyleFactory.create(theme["style"])
    if isinstance(app_or_widget, QApplication):
        app_or_widget.setStyle(style)
        app_or_widget.setStyleSheet(theme["app_stylesheet"])
    else:
        app_or_widget.setStyle(style)
        app_or_widget.setStyleSheet(theme["widget_stylesheet"])
    
    # Apply palette
    palette = QPalette()
    for role, color in theme["palette"].items():
        if isinstance(color, str):
            color = QColor(color)
        palette.setColor(getattr(QPalette.ColorRole, role), color)
    
    if isinstance(app_or_widget, QApplication):
        app_or_widget.setPalette(palette)
    else:
        app_or_widget.setPalette(palette)
    
    # Set font
    if "font_family" in theme or "font_size" in theme:
        font = QFont()
        if "font_family" in theme:
            font.setFamily(theme["font_family"])
        if "font_size" in theme:
            font.setPointSize(theme["font_size"])
        if "font_weight" in theme:
            weight = theme["font_weight"]
            if isinstance(weight, str):
                weight = getattr(QFont.Weight, weight.title())
            font.setWeight(weight)
        
        if isinstance(app_or_widget, QApplication):
            app_or_widget.setFont(font)
        else:
            app_or_widget.setFont(font)


def get_theme_names() -> list[str]:
    """Get a list of available theme names."""
    return list(THEMES.keys())


# Define color palette
COLORS = {
    # Light theme colors
    "light": {
        "primary": "#1a73e8",  # Google blue
        "primary_light": "#e8f0fe",
        "primary_dark": "#1557b0",
        "secondary": "#5f6368",  # Gray
        "background": "#ffffff",
        "surface": "#f5f5f5",
        "error": "#d93025",  # Red
        "success": "#188038",  # Green
        "warning": "#e37400",  # Orange
        "text_primary": "#202124",
        "text_secondary": "#5f6368",
        "text_hint": "#9aa0a6",
        "divider": "#dadce0",
        "border": "#dadce0",
        "hover": "#f1f3f4",
        "selected": "#e8f0fe",
        "highlight": "#f1f3f4",
    },
    # Dark theme colors
    "dark": {
        "primary": "#8ab4f8",  # Lighter blue for better visibility
        "primary_light": "#1e3a8a",
        "primary_dark": "#7baaf7",
        "secondary": "#9aa0a6",
        "background": "#202124",
        "surface": "#2d2d2d",
        "error": "#f28b82",
        "success": "#81c995",
        "warning": "#fbbc04",
        "text_primary": "#e8eaed",
        "text_secondary": "#9aa0a6",
        "text_hint": "#5f6368",
        "divider": "#3c4043",
        "border": "#3c4043",
        "hover": "#3c4043",
        "selected": "#3c4043",
        "highlight": "#3c4043",
    }
}

# Base stylesheet template
BASE_STYLESHEET = """
    QWidget {{
        font-family: {font_family};
        font-size: {font_size}pt;
        color: {text_primary};
    }}
    
    QMainWindow, QDialog {{
        background-color: {background};
    }}
    
    QPushButton, QToolButton, QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, 
    QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QTimeEdit {{
        padding: 4px 8px;
        border: 1px solid {border};
        border-radius: 4px;
        background-color: {surface};
        min-height: 24px;
    }}
    
    QPushButton:hover, QToolButton:hover {{
        background-color: {hover};
    }}
    
    QPushButton:pressed, QToolButton:pressed {{
        background-color: {selected};
    }}
    
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, 
    QDateEdit, QDateTimeEdit, QTimeEdit, QComboBox {{
        background: {surface};
        selection-background-color: {primary};
        selection-color: white;
    }}
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, 
    QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QTimeEdit:focus, 
    QComboBox:focus {{
        border: 1px solid {primary};
    }}
    
    QMenuBar {{
        background-color: {background};
        border: none;
    }}
    
    QMenuBar::item {{
        padding: 4px 8px;
        background: transparent;
    }}
    
    QMenuBar::item:selected {{
        background: {hover};
    }}
    
    QMenu {{
        background-color: {background};
        border: 1px solid {border};
    }}
    
    QMenu::item:selected {{
        background-color: {hover};
    }}
    
    QStatusBar {{
        background: {surface};
        border-top: 1px solid {divider};
    }}
    
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: {surface};
        width: 10px;
        height: 10px;
    }}
    
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {divider};
        border-radius: 5px;
        min-height: 20px;
        min-width: 20px;
    }}
    
    /* Custom widgets */
    #sidebar {{
        background-color: {surface};
        border-right: 1px solid {divider};
    }}
    
    #email-list-item {{
        border-bottom: 1px solid {divider};
        padding: 8px;
    }}
    
    #email-list-item:selected {{
        background-color: {selected};
    }}
"""

# Define themes
THEMES = {
    "light": {
        "name": "Light",
        "style": "Fusion",
        "font_family": "Segoe UI, Arial, sans-serif",
        "font_size": 10,
        "font_weight": "Normal",
        "palette": {
            "Window": COLORS["light"]["background"],
            "WindowText": COLORS["light"]["text_primary"],
            "Base": COLORS["light"]["background"],
            "AlternateBase": COLORS["light"]["surface"],
            "ToolTipBase": COLORS["light"]["background"],
            "ToolTipText": COLORS["light"]["text_primary"],
            "Text": COLORS["light"]["text_primary"],
            "Button": COLORS["light"]["surface"],
            "ButtonText": COLORS["light"]["text_primary"],
            "BrightText": "#ffffff",
            "Link": COLORS["light"]["primary"],
            "Highlight": COLORS["light"]["primary"],
            "HighlightedText": "#ffffff",
        },
        "app_stylesheet": BASE_STYLESHEET.format(**COLORS["light"], 
                                              font_family="Segoe UI, Arial, sans-serif",
                                              font_size=10),
        "widget_stylesheet": """
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
                color: #202124;
            }
        """
    },
    
    "dark": {
        "name": "Dark",
        "style": "Fusion",
        "font_family": "Segoe UI, Arial, sans-serif",
        "font_size": 10,
        "font_weight": "Normal",
        "palette": {
            "Window": COLORS["dark"]["background"],
            "WindowText": COLORS["dark"]["text_primary"],
            "Base": COLORS["dark"]["background"],
            "AlternateBase": COLORS["dark"]["surface"],
            "ToolTipBase": COLORS["dark"]["background"],
            "ToolTipText": COLORS["dark"]["text_primary"],
            "Text": COLORS["dark"]["text_primary"],
            "Button": COLORS["dark"]["surface"],
            "ButtonText": COLORS["dark"]["text_primary"],
            "BrightText": "#ffffff",
            "Link": COLORS["dark"]["primary"],
            "Highlight": COLORS["dark"]["primary"],
            "HighlightedText": "#ffffff",
        },
        "app_stylesheet": BASE_STYLESHEET.format(**COLORS["dark"],
                                              font_family="Segoe UI, Arial, sans-serif",
                                              font_size=10),
        "widget_stylesheet": """
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
                color: #e8eaed;
            }
        """
    }
}
