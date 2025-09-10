#!/bin/bash
# S3 Bucket Diver Launcher Script

# Parse command line arguments
VERBOSE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -v, --verbose    Enable verbose output"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Change to the script directory
if [ "$VERBOSE" = true ]; then
    echo "[VERBOSE] Changing to script directory: $(dirname "$0")"
fi
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "s3_bucket_diver_env" ]; then
    echo "Virtual environment not found. Creating one..."
    if [ "$VERBOSE" = true ]; then
        echo "[VERBOSE] Creating virtual environment with: python3 -m venv s3_bucket_diver_env"
    fi
    python3 -m venv s3_bucket_diver_env
    
    echo "Installing dependencies..."
    if [ "$VERBOSE" = true ]; then
        echo "[VERBOSE] Installing dependencies with: s3_bucket_diver_env/bin/pip install -r requirements.txt"
        s3_bucket_diver_env/bin/pip install -r requirements.txt
    else
        s3_bucket_diver_env/bin/pip install -r requirements.txt > /dev/null 2>&1
    fi
else
    if [ "$VERBOSE" = true ]; then
        echo "[VERBOSE] Virtual environment found at: s3_bucket_diver_env"
    fi
fi

echo "Starting S3 Bucket Diver..."
if [ "$VERBOSE" = true ]; then
    echo "[VERBOSE] Launching with: s3_bucket_diver_env/bin/python s3_browser_app.py --verbose"
    echo "[VERBOSE] Working directory: $(pwd)"
    echo "[VERBOSE] Python version: $(s3_bucket_diver_env/bin/python --version)"
    s3_bucket_diver_env/bin/python s3_browser_app.py --verbose
else
    s3_bucket_diver_env/bin/python s3_browser_app.py
fi
