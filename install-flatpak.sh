#!/bin/bash
# S3 Bucket Diver Flatpak Installer Script

set -e

echo "Installing S3 Bucket Diver Flatpak..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if repo directory exists
if [ ! -d "$SCRIPT_DIR/repo" ]; then
    echo "Error: repo directory not found. Please build the Flatpak first with:"
    echo "flatpak-builder --user --install --force-clean build-dir io.github.jonathands.S3BucketDiver.yml"
    echo "flatpak build-export repo build-dir"
    exit 1
fi

# Add the local repository
echo "Adding local repository..."
flatpak remote-add --user --no-gpg-verify --if-not-exists s3bucketdiver-local "$SCRIPT_DIR/repo"

# Install the application
echo "Installing S3 Bucket Diver..."
flatpak install --user s3bucketdiver-local io.github.jonathands.S3BucketDiver -y

echo "✅ Installation complete!"
echo ""
echo "You can now run S3 Bucket Diver with:"
echo "flatpak run io.github.jonathands.S3BucketDiver"
echo ""
echo "Or find it in your applications menu as 'S3 Bucket Diver'"