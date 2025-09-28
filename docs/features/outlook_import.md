# Outlook Import Feature

## Overview
The Outlook Import feature allows users to import emails from Outlook PST/OST files directly into Phoenix. This enables users to migrate their existing email data from Outlook while maintaining folder structures and metadata.

## Features

### 1. File Selection and Analysis
- Browse and select PST/OST files from the local filesystem
- Automatic analysis of the selected file to extract folder structure and email statistics
- Displays a visual representation of the folder hierarchy

### 2. Folder Mapping
- Map Outlook folders to Phoenix categories and labels
- Visual indicators for mapped folders
- Support for batch mapping multiple folders at once

### 3. Import Process
- Progress tracking with detailed status updates
- Background processing to keep the UI responsive
- Support for cancelling long-running imports
- Automatic retry for failed items

### 4. Import History
- View and manage previous imports
- Detailed statistics for each import
- Option to delete import records

## Prerequisites

To use the Outlook import feature, you need to install the following Python package:

```bash
pip install pypff-python
```

## How to Use

1. **Access the Import Dialog**
   - Open the command palette (`Ctrl+K` or `Cmd+K`)
   - Search for "Import from Outlook"
   - Or use the keyboard shortcut `Ctrl+Shift+O`

2. **Select a File**
   - Click "Browse..." and select your PST or OST file
   - The system will analyze the file and display its contents

3. **Map Folders**
   - Select one or more folders in the tree view
   - Choose a target category and optional label
   - Click "Map Selected" to create the mapping

4. **Start Import**
   - Click "Start Import" to begin the import process
   - Monitor progress in the status bar
   - You can cancel the import at any time

5. **View Results**
   - After completion, view the import results in the "Import History" tab
   - Check for any errors or warnings

## Technical Details

### Data Model

#### OutlookImport
- Represents an import operation
- Tracks file path, status, and statistics
- Linked to the user who performed the import

#### OutlookImportMapping
- Maps Outlook folders to Phoenix categories/labels
- Stores the source path and target category/label
- Tracks the number of items imported

### Database Schema

```sql
CREATE TABLE outlook_imports (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    stats JSON,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE outlook_import_mappings (
    id INTEGER PRIMARY KEY,
    import_id INTEGER REFERENCES outlook_imports(id) ON DELETE CASCADE,
    source_path TEXT NOT NULL,
    category_id INTEGER REFERENCES email_categories(id) ON DELETE SET NULL,
    label_id INTEGER REFERENCES email_labels(id) ON DELETE SET NULL,
    item_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL
);
```

### Error Handling

The import process includes comprehensive error handling:
- File access errors
- Corrupted PST/OST files
- Database constraints
- Network issues (for remote databases)

Errors are logged and displayed to the user with helpful messages.

## Troubleshooting

### Common Issues

1. **File Access Denied**
   - Make sure the file is not in use by another application
   - Check file permissions

2. **Corrupted File**
   - Try running the Microsoft Inbox Repair Tool (SCANPST.EXE) on the file
   - Consider exporting from Outlook to a new PST file and trying again

3. **Missing Dependencies**
   - Ensure `pypff-python` is installed
   - On Windows, you may need Visual C++ Build Tools

### Logging

Detailed logs are available in the application log file. Look for entries with the `outlook_import` logger name.

## Future Enhancements

1. **Incremental Imports**
   - Support for importing only new or modified items

2. **Advanced Mapping**
   - Regular expression based folder mapping
   - Template support for common folder structures

3. **Performance Optimizations**
   - Parallel processing for large imports
   - Improved memory management

4. **Additional Metadata**
   - Support for custom fields
   - Flag and category synchronization
