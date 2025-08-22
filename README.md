# S3 Bucket Diver

## Overview

**S3 Bucket Diver** is a simplistic GUI for quickly connecting to and browsing S3-compatible storage services. It provides basic functionalities such as listing files, uploading, downloading, and deleting objects within buckets.

## Features

- Quick connection setup to S3-compatible storage
- Browse and manage files and folders
- Support for uploading and downloading files
- Basic search and pagination for large file lists
- Export and import connection credentials in JSON format

## Usage

1. Launch the application.
2. Enter your S3 connection details and click `Browse` to view your files.
3. Use the provided controls to manage files in your bucket.

## License

This project is licensed under the GNU Lesser General Public License v3.0.

# S3 Browser - Restructured

A PyQt6-based S3-compatible storage browser with a clean, modular architecture.

## 🏗️ Project Structure

```
s3_browser_py/
├── README.md                 # This file
├── .gitignore               # Git ignore rules
├── s3_browser.py            # Original monolithic version (legacy)
├── s3_browser_app.py        # New restructured main application
│
├── backend/                 # Backend logic and operations
│   ├── __init__.py         # Backend module exports
│   ├── s3_operations.py    # S3 client and file operations
│   └── workers.py          # QThread workers for async operations
│
└── ui/                     # User interface components
    ├── __init__.py         # UI module exports
    ├── connection_widget.py # Connection settings and profiles
    ├── file_list_widget.py  # File listing and navigation
    └── details_widget.py    # File details and action buttons
```

## 🚀 Features

### Core Functionality
- **S3-Compatible Storage**: Works with AWS S3, MinIO, and other S3-compatible services
- **Profile Management**: Save and manage multiple connection profiles
- **Async Operations**: Non-blocking file operations using QThread workers
- **Multi-file Operations**: Upload, download, and delete multiple files/folders

### Virtual Directory Navigation
- **Folder View**: Toggle between flat and hierarchical folder view
- **Deep Navigation**: Navigate into nested folders at any level
- **Breadcrumb Navigation**: See current location and navigate back
- **Double-click Navigation**: Double-click folders to enter them

### Advanced Features
- **Progress Tracking**: Real-time progress for all operations
- **Large File Handling**: Confirmation dialogs for large downloads
- **Error Handling**: Comprehensive error reporting and recovery
- **Memory Efficient**: Handles large file lists efficiently

## 🧩 Architecture

### Backend (`backend/`)

**`s3_operations.py`**
- `S3Client`: Core S3 API wrapper
- `FileProcessor`: File organization and formatting utilities
- `DownloadManager`, `UploadManager`, `DeleteManager`: Operation managers

**`workers.py`**
- `S3Worker`: Async file listing
- `DownloadWorker`, `UploadWorker`, `DeleteWorker`: Async operations

### UI Components (`ui/`)

**`connection_widget.py`**
- Connection settings form
- Profile management (save/load/delete)
- Credential validation

**`file_list_widget.py`**
- File/folder listing with virtual directories
- Navigation controls (back button, breadcrumbs)
- Upload initiation

**`details_widget.py`**
- File/folder details display
- Action buttons (download, delete, copy URL)
- Multi-selection support

### Main Application (`s3_browser_app.py`)
- `S3BrowserMainWindow`: Orchestrates all components
- Signal/slot connections between components
- Operation coordination and error handling

## 🔧 Key Improvements

### Separation of Concerns
- **Backend**: Pure business logic, no UI dependencies
- **UI Components**: Focused, reusable widgets
- **Main App**: Coordination and integration only

### Modularity
- Each component has a single responsibility
- Components communicate via Qt signals/slots
- Easy to test, modify, and extend individual parts

### Maintainability
- Clear module boundaries
- Consistent coding patterns
- Comprehensive documentation

### Extensibility
- Easy to add new UI components
- Backend operations are pluggable
- Signal-based architecture supports new features

## 🏃‍♂️ Running the Application

### New Restructured Version
```bash
python s3_browser_app.py
```

### Legacy Version (for comparison)
```bash
python s3_browser.py
```

## 📋 Requirements

- Python 3.8+
- PyQt6
- boto3

```bash
pip install PyQt6 boto3
```

## 🔒 Security Features

- **Credential Protection**: Profiles stored locally, excluded from git
- **Input Validation**: All connection parameters validated
- **Error Isolation**: Operations failures don't crash the app
- **Memory Safety**: Proper cleanup of worker threads

## 🚀 Future Enhancements

With the new modular architecture, it's easy to add:

- **File Preview**: Add preview widgets for images, text files
- **Sync Operations**: Two-way sync between local and S3
- **Advanced Filters**: Search and filter capabilities
- **Batch Operations**: Queue multiple operations
- **Plugin System**: Custom operation plugins
- **Themes**: Multiple UI themes and layouts

## 📝 Development Notes

### Adding New UI Components
1. Create new widget in `ui/` directory
2. Add to `ui/__init__.py` exports
3. Connect signals in `s3_browser_app.py`

### Adding New Operations
1. Create operation class in `backend/s3_operations.py`
2. Create worker class in `backend/workers.py`
3. Add signal handling in main application

### Testing Components
Each component can be tested independently:
```python
from ui import ConnectionWidget
# Test connection widget in isolation
```

## 🎯 Benefits of Restructuring

1. **Code Organization**: Clear separation between UI and business logic
2. **Reusability**: UI components can be reused in other applications
3. **Testing**: Individual components can be unit tested
4. **Maintenance**: Easier to locate and fix bugs
5. **Team Development**: Multiple developers can work on different components
6. **Documentation**: Each module is self-contained and documented

The new architecture maintains all existing functionality while providing a solid foundation for future enhancements!

# S3-Compatible Storage Browser

A PyQt6-based GUI application for browsing S3-compatible storage systems.

## Features

- **🔗 Universal S3 Compatibility** - Connect to any S3-compatible storage service (AWS S3, MinIO, DigitalOcean Spaces, etc.)
- **💾 Credential Profile Management** - Save, load, and manage multiple connection profiles
- **📋 Enhanced UI Layout** - Clean 3-row layout with proper spacing for credentials
- **📁 File Browser** - List all files in a bucket with details (size, modified date, storage class)
- **📥 Multi-File Downloads** - Select and download multiple files simultaneously with progress tracking
- **🎯 Smart Selection** - Extended selection support (Ctrl+Click, Shift+Click for ranges)
- **🔍 File Details** - View comprehensive file metadata for single or multiple selections
- **📋 URL Copy** - Copy file URLs to clipboard
- **⚡ Asynchronous Operations** - Non-blocking UI during network operations and downloads
- **🛡️ Comprehensive Error Handling** - Graceful handling of connection, authentication, and download errors

## Requirements

- Python 3.8+
- PyQt6
- boto3

## Installation

### Option 1: Using the launcher script (Recommended)
```bash
./run_s3_browser.sh
```
The launcher script will automatically create a virtual environment and install dependencies if needed.

### Option 2: Manual installation
1. Create a virtual environment:
```bash
python3 -m venv s3_browser_env
```

2. Install the required dependencies:
```bash
s3_browser_env/bin/pip install -r requirements.txt
```

3. Run the application:
```bash
s3_browser_env/bin/python s3_browser.py
```

## Usage

1. **Configure Connection Settings:**
   - **Endpoint URL**: The S3 endpoint URL (e.g., `https://s3.amazonaws.com` for AWS, `https://your-minio-server:9000` for MinIO)
   - **Bucket**: The name of the bucket you want to browse
   - **Access Key**: Your S3 access key ID
   - **Secret Key**: Your S3 secret access key

2. **Connect and Browse:**
   - Fill in all connection fields
   - Click "Connect & List Files"
   - The application will connect to the S3 service and list all files in the bucket

3. **Credential Profile Management:**
   - **Save Profile**: Click "Save Profile" to save the current connection settings with a custom name
   - **Load Profile**: Select a saved profile from the dropdown to automatically fill in connection details
   - **Delete Profile**: Select a profile and click "Delete" to remove it permanently
   - Profiles are stored in `~/.s3_browser_profiles.json`

4. **File Selection & Operations:**
   - **Single Selection**: Click a file to view its details and enable download
   - **Multiple Selection**: Use Ctrl+Click to select multiple files, or Shift+Click for ranges
   - **Download Files**: Click "Download" (or "Download X Files") to save selected files to your computer
   - **View Details**: Selected files show total size and file list in the details panel
   - **Copy URLs**: Copy file URLs to clipboard (works with currently highlighted file)

5. **Download Process:**
   - Choose download directory when downloading files
   - Real-time progress tracking with current file being downloaded
   - Automatic duplicate filename handling (appends _1, _2, etc.)
   - Download confirmation for large file sets (>100MB)
   - Complete download summary showing successful vs failed downloads

## Supported S3-Compatible Services

- Amazon S3
- MinIO
- DigitalOcean Spaces
- Backblaze B2
- Wasabi
- Any other S3-compatible storage service

## Security Notes

- Credentials are only stored in memory during the application session
- Use the "Show credentials" checkbox to verify your credentials if needed
- For production use, consider implementing credential storage with encryption

## Extending the Application

The application is designed to be easily extensible. You can add features like:

- File upload functionality
- File download implementation
- Bucket management (create, delete buckets)
- File operations (delete, rename files)
- Folder/prefix navigation
- Search and filtering capabilities

## Error Handling

The application handles common S3 errors including:
- Invalid credentials
- Connection timeouts
- Non-existent buckets
- Access denied errors
- Network connectivity issues

## License

This project is open source and available under the MIT License.
