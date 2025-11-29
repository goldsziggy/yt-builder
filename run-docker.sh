#!/bin/bash
# Helper script to run yt-builder in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    print_error "Docker Compose is not available."
    exit 1
fi

# Determine docker-compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Check if image exists, if not build it
if ! docker images | grep -q "yt-builder"; then
    print_info "Docker image not found. Building it now..."
    $COMPOSE_CMD build
    print_info "Docker image built successfully!"
else
    print_info "Using existing Docker image"
fi

# Check if any media directories are empty
media_warnings=0

if [ ! "$(ls -A videos/)" ]; then
    print_warn "videos/ directory is empty. Add video files to continue."
    media_warnings=$((media_warnings + 1))
fi

if [ ! "$(ls -A music/)" ]; then
    print_warn "music/ directory is empty. Video will be created without music."
fi

if [ ! "$(ls -A quotes/)" ]; then
    print_warn "quotes/ directory is empty. Video will be created without quotes."
fi

if [ $media_warnings -gt 0 ]; then
    print_error "Cannot proceed: videos/ directory is required and must not be empty."
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p output

# If no arguments provided, show help
if [ $# -eq 0 ]; then
    print_info "Running yt-builder with --help"
    echo ""
    $COMPOSE_CMD run --rm yt-builder --help
    echo ""
    print_info "Example usage:"
    echo "  $0 --duration 60 --quotes-duration 5 --quotes-min-between 10 --quotes-max-between 20 -o /app/output/test.mp4"
    exit 0
fi

# Run the container with provided arguments
print_info "Running yt-builder with Docker..."
echo ""

$COMPOSE_CMD run --rm yt-builder "$@"

# Check if output was created
if [ -n "$(ls -A output/ 2>/dev/null)" ]; then
    echo ""
    print_info "Success! Output files:"
    ls -lh output/
else
    echo ""
    print_warn "No output files found. Check the logs above for errors."
fi
