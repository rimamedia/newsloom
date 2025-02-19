#!/bin/bash
set -e  # Exit on error

# Show usage instructions
show_usage() {
    echo "Usage: $0 [-b branch] [-h]"
    echo "Build the frontend from a specific branch"
    echo ""
    echo "Options:"
    echo "  -b branch    Specify the git branch to build from (default: main)"
    echo "  -h          Show this help message"
    exit 1
}

# Configuration
FRONTEND_REPO="git@github.com:rimamedia/newsloom-frontend.git"
FRONTEND_BRANCH="main"  # Default branch
BUILD_DIR="frontend-build"
DIST_DIR="frontend-dist"

# Parse command line arguments
while getopts "b:h" opt; do
    case $opt in
        b)
            FRONTEND_BRANCH="$OPTARG"
            ;;
        h)
            show_usage
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            show_usage
            ;;
    esac
done

# Clean previous builds (with sudo if needed)
if [ -d "$BUILD_DIR" ] || [ -d "$DIST_DIR" ]; then
    echo "Cleaning previous builds (may require sudo)..."
    sudo rm -rf $BUILD_DIR $DIST_DIR
fi

# Clone and build
echo "Cloning from branch: $FRONTEND_BRANCH"
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
