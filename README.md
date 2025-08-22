# S3 Bucket Diver

A simple Qt6 GUI application for browsing S3-compatible storage services.

## Features

- Connect to any S3-compatible storage service (AWS S3, MinIO, DigitalOcean Spaces, etc.)
- Browse and manage files and folders
- Upload, download, and delete files
- Search and pagination for large file lists
- Save and manage connection profiles
- Export and import credentials as JSON

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

## Usage

1. Launch the application
2. Enter your S3 connection details (endpoint, bucket, access key, secret key)
3. Click "Browse" to connect and view your files
4. Use the interface to upload, download, or delete files

## Supported Services

- Amazon S3
- MinIO
- DigitalOcean Spaces
- Backblaze B2
- Wasabi
- Any other S3-compatible storage service

## License

Licensed under LGPL-3.0 for Qt6 compatibility.
