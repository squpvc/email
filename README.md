# Project Phoenix

![Project Phoenix Logo](https://raw.githubusercontent.com/yourusername/email/main/assets/logo.png)

A modern, AI-powered email client with integrated productivity features, built with Python and PyQt6.

## ✨ Features

- **Modern Email Client**: Full-featured email management with support for multiple accounts
- **AI-Powered**: Smart replies, email summarization, and intelligent search
- **Cross-Platform**: Works on Windows and Linux (macOS support coming soon)
- **Themes**: Light and dark themes with system preference detection
- **Command Palette**: Quick access to all features via `Ctrl+K`
- **Smart Search**: Find emails using natural language queries
- **Responsive UI**: Clean, modern interface that adapts to your workflow
- **Outlook Import**: Easily migrate emails from Outlook PST/OST files with folder mapping

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git (optional, for development)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/email.git
   cd email
   ```

2. **Create and activate a virtual environment** (recommended):
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python -m phoenix
   ```

## 🎯 First Run

1. On first launch, Phoenix will create necessary configuration files in `~/.phoenix/`
2. Add your email account through the settings menu
3. Use `Ctrl+K` to open the command palette and explore available features

## 🎨 Features in Detail

### Email Management
- Unified inbox for all your email accounts
- Threaded conversations
- Rich text composition
- Email filtering and searching
- Custom folders and labels
- **Outlook Import**: Import emails from PST/OST files with folder mapping to categories/labels

### AI Capabilities
- **Smart Replies**: Context-aware response suggestions
- **Email Summarization**: Get concise overviews of long threads
- **Action Extraction**: Automatically identify tasks and follow-ups
- **Semantic Search**: Find emails using natural language queries

### Productivity Tools
- Built-in task management
- Calendar integration
- Contact management
- Custom keyboard shortcuts

## ⌨️ Keyboard Shortcuts

| Shortcut       | Action                     |
|----------------|----------------------------|
| `Ctrl+K`       | Open command palette       |
| `Ctrl+N`       | New email                  |
| `Ctrl+R`       | Reply to email             |
| `Ctrl+Shift+R` | Reply all                  |
| `Ctrl+F`       | Forward email              |
| `Ctrl+E`       | Archive email              |
| `Del`          | Delete email               |
| `Ctrl+Shift+T` | Toggle theme               |
| `Ctrl++`/`-`   | Adjust UI zoom             |
| `Ctrl+0`       | Reset zoom                 |
| `Ctrl+\`       | Toggle sidebar             |
| `Ctrl+Shift+O` | Import from Outlook        |
| `F5`           | Refresh email              |

## 🛠️ Requirements

- Python 3.9+
- PyQt6
- SQLite 3.35+
- See `requirements.txt` for complete dependency list

## 📦 Project Structure

```
phoenix/
├── application.py        # Main application class
├── config.py            # Configuration settings
├── database.py          # Database models and operations
├── models/              # Data models
│   └── outlook_import.py # Outlook import models
├── ui/                  # User interface components
│   ├── main_window.py   # Main window implementation
│   ├── dialogs/         # Dialog windows
│   │   └── outlook_import_dialog.py  # Outlook import dialog
│   └── widgets/         # Custom UI widgets
├── commands/            # Command implementations
│   └── outlook_import.py # Outlook import command
├── importers/           # Email importers
│   └── outlook.py       # Outlook PST/OST importer
├── utils/               # Utility modules
│   ├── database.py      # Database utilities
│   ├── logging.py       # Logging configuration
│   └── theme.py         # Theme management
└── ai/                  # AI-related functionality
    ├── commands.py      # AI command handlers
    └── services.py      # Core AI services
```

## 📚 Documentation

For detailed documentation on specific features, check out the [docs](docs/) directory:

- [Outlook Import Feature](docs/features/outlook_import.md) - Guide to importing emails from Outlook

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to get started.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📧 Contact

For questions or support, please [open an issue](https://github.com/yourusername/email/issues) on GitHub.

## 🙏 Acknowledgments

- Built with ❤️ using Python and PyQt6
- Inspired by modern email clients like Spark and Mailspring
- Special thanks to all contributors

---

<p align="center">
  Made with ❤️ by the Project Phoenix Team
</p>