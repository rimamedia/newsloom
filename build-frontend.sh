#!/bin/bash
set -e  # Exit on error

# Usage information
usage() {
    echo "Usage: $0 [branch_name]"
    echo "  branch_name: Optional. The frontend repository branch to build (default: main)"
    echo ""
    echo "Example:"
    echo "  $0                # Build using the main branch"
    echo "  $0 develop        # Build using the develop branch"
    echo "  $0 feature/login  # Build using the feature/login branch"
    exit 1
}

# Check if help is requested
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
fi

# Configuration
FRONTEND_REPO="git@github.com:rimamedia/newsloom-frontend.git"
FRONTEND_BRANCH=${1:-"main"}  # Use provided branch or default to "main"
BUILD_DIR="frontend-build"
DIST_DIR="frontend-dist"

echo "Building frontend from branch: $FRONTEND_BRANCH"

# Clean previous builds (with sudo if needed)
if [ -d "$BUILD_DIR" ] || [ -d "$DIST_DIR" ]; then
    echo "Cleaning previous builds (may require sudo)..."
    sudo rm -rf $BUILD_DIR $DIST_DIR
fi

# Clone and build
git clone -b $FRONTEND_BRANCH $FRONTEND_REPO $BUILD_DIR
cd $BUILD_DIR

# Create development environment file
cat > .env << EOL
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_BASE_URL=http://localhost:8000
EOL

# Build
npm install
npm run build

# Handle all build artifacts with sudo
cd ..
echo "Moving build files and cleaning up..."
sudo bash -c "
    mv $BUILD_DIR/dist $DIST_DIR && \
    rm -rf $BUILD_DIR && \
    chown -R $USER:$(id -gn) $DIST_DIR
"
