#!/bin/bash
set -e  # Exit on error

# Configuration
FRONTEND_REPO="git@github.com:rimamedia/newsloom-frontend.git"
FRONTEND_BRANCH="main"
BUILD_DIR="frontend-build"
DIST_DIR="frontend-dist"

# Clean previous builds (with sudo if needed)
if [ -d "$BUILD_DIR" ] || [ -d "$DIST_DIR" ]; then
    echo "Cleaning previous builds (may require sudo)..."
    sudo rm -rf $BUILD_DIR $DIST_DIR
fi

# Clone and build
git clone $FRONTEND_REPO $BUILD_DIR
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
