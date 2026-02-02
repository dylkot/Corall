#!/bin/bash
#
# Build script for Corall standalone application
#
# Usage:
#   ./scripts/build_app.sh           # Build for current platform
#   ./scripts/build_app.sh --clean   # Clean build (removes previous builds)
#   ./scripts/build_app.sh --help    # Show help
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Application info
APP_NAME="Corall"
VERSION="1.0.0"

# Detect platform
detect_platform() {
    case "$(uname -s)" in
        Darwin*)    PLATFORM="macos" ;;
        Linux*)     PLATFORM="linux" ;;
        MINGW*|CYGWIN*|MSYS*) PLATFORM="windows" ;;
        *)          PLATFORM="unknown" ;;
    esac
    echo "$PLATFORM"
}

# Print colored message
print_msg() {
    local color=$1
    local msg=$2
    echo -e "${color}${msg}${NC}"
}

# Print step message
step() {
    print_msg "$BLUE" "=> $1"
}

# Print success message
success() {
    print_msg "$GREEN" "   $1"
}

# Print warning message
warn() {
    print_msg "$YELLOW" "   Warning: $1"
}

# Print error and exit
error() {
    print_msg "$RED" "   Error: $1"
    exit 1
}

# Show help
show_help() {
    cat << EOF
Corall Build Script
==================

Build a standalone application for the current platform.

Usage:
    $0 [options]

Options:
    --clean     Clean previous builds before building
    --help      Show this help message
    --no-venv   Skip virtual environment creation (use existing)

Output:
    macOS:      dist/Corall.app
    Windows:    dist/Corall/Corall.exe
    Linux:      dist/Corall/Corall

Requirements:
    - Python 3.8 or higher
    - pip

The script will:
    1. Create a virtual environment for building
    2. Install dependencies
    3. Run PyInstaller to create the standalone app
    4. Package the result for distribution

EOF
}

# Clean previous builds
clean_build() {
    step "Cleaning previous builds..."
    rm -rf "$PROJECT_ROOT/build"
    rm -rf "$PROJECT_ROOT/dist"
    rm -rf "$PROJECT_ROOT/.build_venv"
    success "Cleaned"
}

# Check Python version
check_python() {
    step "Checking Python version..."

    # Try python3 first, then python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        error "Python not found. Please install Python 3.8 or higher."
    fi

    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
        error "Python 3.8 or higher required. Found: $PYTHON_VERSION"
    fi

    success "Found Python $PYTHON_VERSION"
}

# Create virtual environment
create_venv() {
    step "Creating build virtual environment..."

    VENV_DIR="$PROJECT_ROOT/.build_venv"

    if [ -d "$VENV_DIR" ] && [ "$USE_EXISTING_VENV" = true ]; then
        success "Using existing virtual environment"
    else
        rm -rf "$VENV_DIR"
        $PYTHON_CMD -m venv "$VENV_DIR"
        success "Created virtual environment at $VENV_DIR"
    fi

    # Activate virtual environment
    if [ "$PLATFORM" = "windows" ]; then
        source "$VENV_DIR/Scripts/activate"
    else
        source "$VENV_DIR/bin/activate"
    fi

    success "Activated virtual environment"
}

# Install dependencies
install_deps() {
    step "Installing dependencies..."

    # Upgrade pip
    pip install --upgrade pip > /dev/null 2>&1

    # Install requirements
    pip install -r "$PROJECT_ROOT/requirements.txt" > /dev/null 2>&1
    success "Installed application dependencies"

    # Install build dependencies
    pip install pyinstaller > /dev/null 2>&1
    success "Installed PyInstaller"
}

# Download and cache the sentence-transformers model
cache_model() {
    step "Pre-downloading ML model (this may take a moment)..."

    python -c "
from sentence_transformers import SentenceTransformer
print('   Downloading all-MiniLM-L6-v2 model...')
model = SentenceTransformer('all-MiniLM-L6-v2')
print('   Model cached successfully')
" 2>&1 | grep -v "^$"

    success "ML model cached"
}

# Build the application
build_app() {
    step "Building standalone application..."

    cd "$PROJECT_ROOT"

    # Run PyInstaller
    pyinstaller \
        --noconfirm \
        --clean \
        --log-level WARN \
        "packaging/corall.spec"

    success "Build completed"
}

# Post-build steps
post_build() {
    step "Finalizing build..."

    PLATFORM=$(detect_platform)

    case "$PLATFORM" in
        macos)
            if [ -d "$PROJECT_ROOT/dist/$APP_NAME.app" ]; then
                success "macOS app bundle created: dist/$APP_NAME.app"

                # Create a DMG (optional, requires create-dmg)
                if command -v create-dmg &> /dev/null; then
                    step "Creating DMG installer..."
                    create-dmg \
                        --volname "$APP_NAME" \
                        --window-pos 200 120 \
                        --window-size 600 400 \
                        --icon-size 100 \
                        --icon "$APP_NAME.app" 175 190 \
                        --app-drop-link 425 190 \
                        "dist/${APP_NAME}-${VERSION}.dmg" \
                        "dist/$APP_NAME.app" 2>/dev/null || warn "DMG creation failed (optional)"
                fi
            fi
            ;;

        windows)
            success "Windows executable created: dist/$APP_NAME/$APP_NAME.exe"
            ;;

        linux)
            success "Linux executable created: dist/$APP_NAME/$APP_NAME"

            # Make executable
            chmod +x "$PROJECT_ROOT/dist/$APP_NAME/$APP_NAME" 2>/dev/null || true
            ;;
    esac
}

# Print build summary
print_summary() {
    echo ""
    print_msg "$GREEN" "============================================"
    print_msg "$GREEN" " Build completed successfully!"
    print_msg "$GREEN" "============================================"
    echo ""

    PLATFORM=$(detect_platform)

    echo "Output location:"
    case "$PLATFORM" in
        macos)
            echo "  App:  $PROJECT_ROOT/dist/$APP_NAME.app"
            echo ""
            echo "To run:"
            echo "  open dist/$APP_NAME.app"
            echo ""
            echo "To install:"
            echo "  cp -r dist/$APP_NAME.app /Applications/"
            ;;

        windows)
            echo "  Folder: $PROJECT_ROOT/dist/$APP_NAME/"
            echo "  EXE:    $PROJECT_ROOT/dist/$APP_NAME/$APP_NAME.exe"
            ;;

        linux)
            echo "  Folder: $PROJECT_ROOT/dist/$APP_NAME/"
            echo "  Binary: $PROJECT_ROOT/dist/$APP_NAME/$APP_NAME"
            echo ""
            echo "To run:"
            echo "  ./dist/$APP_NAME/$APP_NAME"
            ;;
    esac

    echo ""
    echo "Data directory (created on first run):"
    case "$PLATFORM" in
        macos)   echo "  ~/Library/Application Support/Corall/" ;;
        windows) echo "  %APPDATA%/Corall/" ;;
        linux)   echo "  ~/.local/share/Corall/" ;;
    esac
    echo ""
}

# Main function
main() {
    CLEAN=false
    USE_EXISTING_VENV=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                CLEAN=true
                shift
                ;;
            --no-venv)
                USE_EXISTING_VENV=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1. Use --help for usage."
                ;;
        esac
    done

    echo ""
    print_msg "$BLUE" "============================================"
    print_msg "$BLUE" " Building $APP_NAME v$VERSION"
    print_msg "$BLUE" "============================================"
    echo ""

    PLATFORM=$(detect_platform)
    step "Detected platform: $PLATFORM"

    if [ "$PLATFORM" = "unknown" ]; then
        error "Unknown platform. Build only supported on macOS, Windows, and Linux."
    fi

    if [ "$CLEAN" = true ]; then
        clean_build
    fi

    check_python
    create_venv
    install_deps
    cache_model
    build_app
    post_build
    print_summary
}

# Run main function
main "$@"
