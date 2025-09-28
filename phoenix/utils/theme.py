"""
Theme management for Project Phoenix.
"""
from typing import Dict, Any, Optional, Union

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication, QWidget, QStyleFactory, QStyle

# Default theme colors
THEMES = {
    "light": {
        "name": "Light",
        "palette": {
            "window": "#f0f0f0",
            "window_text": "#000000",
            "base": "#ffffff",
            "alternate_base": "#f0f0f0",
            "text": "#000000",
            "button": "#e0e0e0",
            "button_text": "#000000",
            "bright_text": "#ffffff",
            "highlight": "#0078d7",
            "highlighted_text": "#ffffff",
            "link": "#0066cc",
            "link_visited": "#800080",
        },
        "font": {
            "family": "Segoe UI",
            "size": 9,
        },
    },
    "dark": {
        "name": "Dark",
        "palette": {
            "window": "#2d2d2d",
            "window_text": "#ffffff",
            "base": "#252525",
            "alternate_base": "#3c3c3c",
            "text": "#ffffff",
            "button": "#3c3c3c",
            "button_text": "#ffffff",
            "bright_text": "#ffffff",
            "highlight": "#0078d7",
            "highlighted_text": "#ffffff",
            "link": "#4da6ff",
            "link_visited": "#c586c0",
        },
        "font": {
            "family": "Segoe UI",
            "size": 9,
        },
    },
}

class ThemeManager:
    """Manages application theming and styles."""
    
    def __init__(self, app: QApplication):
        """Initialize the theme manager with the application instance."""
        self.app = app
        self.current_theme = "light"
    
    def toggle_theme(self) -> str:
        """Toggle between light and dark themes.
        
        Returns:
            str: The name of the newly applied theme ("light" or "dark")
        """
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(new_theme)
        return new_theme
        
    def apply_theme(self, theme_name: str = "light") -> None:
        """Apply a theme to the application.
        
        Args:
            theme_name: Name of the theme to apply ("light" or "dark")
        """
        if theme_name not in THEMES:
            theme_name = "light"
            
        self.current_theme = theme_name
        theme = THEMES[theme_name]
        
        # Apply style
        self.app.setStyle("Fusion")
        
        # Create and set palette
        palette = QPalette()
        colors = theme["palette"]
        
        # Set colors
        palette.setColor(QPalette.ColorRole.Window, QColor(colors["window"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["window_text"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors["base"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["alternate_base"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors["button"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["button_text"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["bright_text"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["highlight"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["highlighted_text"]))
        palette.setColor(QPalette.ColorRole.Link, QColor(colors["link"]))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(colors["link_visited"]))
        
        self.app.setPalette(palette)
        
        # Set font
        font = QFont(theme["font"]["family"], theme["font"]["size"])
        self.app.setFont(font)
        
        # Apply style sheet for additional theming
        self.app.setStyleSheet(f"""
            QToolTip {{
                color: {colors["text"]};
                background-color: {colors["base"]};
                border: 1px solid {colors["window"]};
            }}
            QMenu::item:selected {{
                background-color: {colors["highlight"]};
                color: {colors["highlighted_text"]};
            }}
        """)
    
    def get_available_themes(self) -> list:
        """Get a list of available theme names."""
        return list(THEMES.keys())
    
    def get_current_theme(self) -> str:
        """Get the name of the current theme."""
        return self.current_theme

def apply_theme(app_or_widget: Union[QApplication, QWidget], theme_name: str = "light") -> None:
    """Apply a theme to the application or widget.
    
    Args:
        app_or_widget: The QApplication or QWidget to apply the theme to
        theme_name: Name of the theme to apply ("light" or "dark")
    """
    if theme_name not in THEMES:
        theme_name = "light"
        
    theme = THEMES[theme_name]
    
    # Apply style
    if isinstance(app_or_widget, QApplication):
        app_or_widget.setStyle("Fusion")
    
    # Create and set palette
    palette = QPalette()
    colors = theme["palette"]
    
    # Set colors
    palette.setColor(QPalette.ColorRole.Window, QColor(colors["window"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["window_text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["base"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["alternate_base"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["button"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["button_text"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["bright_text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["highlight"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["highlighted_text"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(colors["link"]))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(colors["link_visited"]))
    
    if isinstance(app_or_widget, QApplication):
        app_or_widget.setPalette(palette)
    else:
        app_or_widget.setPalette(palette)
    
    # Set font
    font = QFont(theme["font"]["family"], theme["font"]["size"])
    if isinstance(app_or_widget, QApplication):
        app_or_widget.setFont(font)
    else:
        app_or_widget.setFont(font)
    
    # Apply style sheet for additional theming
    style_sheet = f"""
        QToolTip {{
            color: {colors["text"]};
            background-color: {colors["base"]};
            border: 1px solid {colors["window"]};
        }}
        QMenu::item:selected {{
            background-color: {colors["highlight"]};
            color: {colors["highlighted_text"]};
        }}
    """
    
    if isinstance(app_or_widget, QApplication):
        app_or_widget.setStyleSheet(style_sheet)
    else:
        app_or_widget.setStyleSheet(style_sheet)

def get_theme_names() -> list:
    """Get a list of available theme names."""
    return list(THEMES.keys())
