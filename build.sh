#!/bin/bash
# S3 Bucket Diver Comprehensive Build Script
# Builds both Flatpak and PyInstaller executables

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "S3 Bucket Diver Build Script"
print_status "=============================="

# Check if we should build PyInstaller executable
BUILD_PYINSTALLER=true
BUILD_FLATPAK=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-pyinstaller)
            BUILD_PYINSTALLER=false
            shift
            ;;
        --no-flatpak)
            BUILD_FLATPAK=false
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --no-pyinstaller    Skip PyInstaller build"
            echo "  --no-flatpak        Skip Flatpak build"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# PyInstaller Build
if [ "$BUILD_PYINSTALLER" = true ]; then
    print_status "Building PyInstaller executable..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "pyinstaller_env" ]; then
        print_status "Creating PyInstaller virtual environment..."
        python3 -m venv pyinstaller_env
        pyinstaller_env/bin/pip install --upgrade pip
        pyinstaller_env/bin/pip install pyinstaller PyQt6 boto3 requests
    fi
    
    # Build the executable
    print_status "Building standalone executable with PyInstaller..."
    pyinstaller_env/bin/pyinstaller s3_bucket_diver.spec
    
    if [ -f "dist/S3BucketDiver" ]; then
        print_status "✅ PyInstaller build successful!"
        print_status "Executable location: $SCRIPT_DIR/dist/S3BucketDiver"
        print_status "Size: $(du -h dist/S3BucketDiver | cut -f1)"
    else
        print_error "❌ PyInstaller build failed!"
        exit 1
    fi
fi

# Flatpak Build
if [ "$BUILD_FLATPAK" = true ]; then
    print_status "Building Flatpak package..."
    
    # Check if flatpak-builder is available
    if ! command -v flatpak-builder &> /dev/null; then
        print_error "flatpak-builder is not installed. Please install it first:"
        print_error "sudo apt install flatpak-builder"
        exit 1
    fi
    
    # Build Flatpak
    print_status "Building Flatpak with flatpak-builder..."
    flatpak-builder --user --install --force-clean build-dir io.github.jonathands.S3BucketDiver.yml
    
    # Export to repository
    print_status "Exporting Flatpak to repository..."
    flatpak build-export repo build-dir
    flatpak build-update-repo repo
    
    # Add local repository if not already added
    if ! flatpak remote-list --user | grep -q "s3bucketdiver-local"; then
        print_status "Adding local repository..."
        flatpak remote-add --user --no-gpg-verify s3bucketdiver-local "$SCRIPT_DIR/repo"
    fi
    
    # Update flatpakref file
    print_status "Updating flatpakref file..."
    cat > io.github.jonathands.S3BucketDiver.flatpakref << EOF
[Flatpak Ref]
Name=io.github.jonathands.S3BucketDiver
Branch=master
Title=S3 Bucket Diver
IsRuntime=false
Url=file://$(echo "$SCRIPT_DIR/repo" | sed 's/ /%20/g')
GPGKey=
RuntimeRepo=https://flathub.org/repo/flathub.flatpakrepo
Comment=Browse and manage S3-compatible storage services
EOF
    
    # Install/Update the Flatpak
    print_status "Installing/updating Flatpak locally..."
    if flatpak list --user | grep -q "io.github.jonathands.S3BucketDiver"; then
        print_status "Updating existing Flatpak installation..."
        flatpak update --user io.github.jonathands.S3BucketDiver -y
    else
        print_status "Installing Flatpak for the first time..."
        flatpak install --user s3bucketdiver-local io.github.jonathands.S3BucketDiver -y
    fi
    
    print_status "✅ Flatpak build and installation successful!"
fi

# Create distribution package
print_status "Creating distribution package..."
DIST_NAME="s3-bucket-diver-$(date +%Y%m%d-%H%M%S)"
mkdir -p "distributions/$DIST_NAME"

if [ "$BUILD_PYINSTALLER" = true ] && [ -f "dist/S3BucketDiver" ]; then
    cp dist/S3BucketDiver "distributions/$DIST_NAME/"
    print_status "✅ PyInstaller executable copied to distribution"
fi

if [ "$BUILD_FLATPAK" = true ] && [ -f "io.github.jonathands.S3BucketDiver.flatpakref" ]; then
    cp -r repo "distributions/$DIST_NAME/"
    cp io.github.jonathands.S3BucketDiver.flatpakref "distributions/$DIST_NAME/"
    cp install-flatpak.sh "distributions/$DIST_NAME/"
    print_status "✅ Flatpak files copied to distribution"
fi

# Create README for distribution
cat > "distributions/$DIST_NAME/README.md" << EOF
# S3 Bucket Diver Distribution Package

This package contains distribution files for S3 Bucket Diver.

## Contents

EOF

if [ "$BUILD_PYINSTALLER" = true ] && [ -f "distributions/$DIST_NAME/S3BucketDiver" ]; then
    cat >> "distributions/$DIST_NAME/README.md" << EOF
### Standalone Executable (PyInstaller)
- \`S3BucketDiver\` - Standalone executable (no installation required)
- Simply run: \`./S3BucketDiver\`

EOF
fi

if [ "$BUILD_FLATPAK" = true ] && [ -f "distributions/$DIST_NAME/io.github.jonathands.S3BucketDiver.flatpakref" ]; then
    cat >> "distributions/$DIST_NAME/README.md" << EOF
### Flatpak Package
- \`repo/\` - Flatpak repository
- \`io.github.jonathands.S3BucketDiver.flatpakref\` - Flatpak reference file
- \`install-flatpak.sh\` - Installation script

To install Flatpak version:
\`\`\`bash
./install-flatpak.sh
\`\`\`

Or manually:
\`\`\`bash
flatpak remote-add --user --no-gpg-verify s3bucketdiver-local ./repo
flatpak install --user s3bucketdiver-local io.github.jonathands.S3BucketDiver
\`\`\`

EOF
fi

cat >> "distributions/$DIST_NAME/README.md" << EOF
## System Requirements

- Linux x86_64
- For Flatpak: flatpak runtime support
- For standalone: No additional requirements

## Usage

Run the application and connect to your S3-compatible storage service using the connection dialog.

Generated on: $(date)
EOF

print_status "✅ Distribution package created: distributions/$DIST_NAME"

# Summary
print_status ""
print_status "🎉 Build Complete!"
print_status "=================="

if [ "$BUILD_PYINSTALLER" = true ]; then
    print_status "PyInstaller executable: dist/S3BucketDiver"
    print_status "  Run with: ./dist/S3BucketDiver"
fi

if [ "$BUILD_FLATPAK" = true ]; then
    print_status "Flatpak installed and ready to use:"
    print_status "  Run with: flatpak run io.github.jonathands.S3BucketDiver"
    print_status "  Or find it in your applications menu"
fi

print_status "Distribution package: distributions/$DIST_NAME"
print_status ""
print_status "Happy S3 browsing! 🪣✨"