# S3 Bucket Diver

This is a very simple GUI application for browsing and managing S3 compatible storage services.

<img width="1035" height="759" alt="s3-bucket-diver-screenshot" src="https://github.com/user-attachments/assets/40840225-935e-481e-a76f-0eaa0a0c1735" />


## Features

- Connect to S3-compatible storage services
- Browse and manage files and virtual directories
- Upload, download, and delete files
- Search and pagination for large file lists
- Save and manage connection profiles
- Export and import credentials as JSON
- Drag and drop directories/files directly on the files list

## Requirements

- Python 3.8+
- PyQt6
- boto3

## Installation

### From Source
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python s3_browser_app.py`

### Using the Launcher Script
```bash
chmod +x run.sh
./run.sh
```
_Use the -v flag for verbose output in the shell_


## Usage

1. Launch the application
2. Enter your S3 connection details (endpoint, bucket, access key, secret key)
3. Click "Browse" to connect and view your files
4. Use the interface to upload, download, or delete files

## Tested Services

- Amazon S3
- CloudFlare R2
- Oracle Cloud S3 Storage

## License
Licensed under LGPL-3.0 (because Qt requires it)

## TODO
- [ ] Fix/Warn user about a bug on the virtual directory listing when the file list is very long
- [ ] Fix flatpak build and release 
- [ ] Add the ability to work with files en masse without having to select them one by one (downloading/deleting large buckets)
