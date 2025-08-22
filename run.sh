#!/bin/bash
# S3 Bucket Diver Launcher Script

# Change to the script directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "s3_bucket_diver_env" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv s3_bucket_diver_env
    echo "Installing dependencies..."
    s3_bucket_diver_env/bin/pip install -r requirements.txt
fi

echo "Starting S3 Bucket Diver..."
s3_bucket_diver_env/bin/python s3_browser_app.py
