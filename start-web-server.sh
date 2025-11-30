#!/bin/bash

# YouTube Video Builder - Web Server Launcher
# This script starts the web interface for easy video configuration and building

set -e

echo "🎬 YouTube Video Builder - Web Server"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Error: Python is not installed"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "✓ Python found: $($PYTHON_CMD --version)"

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  Warning: FFmpeg not found"
    echo "Please install FFmpeg to process videos:"
    echo "  - macOS: brew install ffmpeg"
    echo "  - Ubuntu: sudo apt-get install ffmpeg"
    echo ""
fi

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Create required directories
echo "📁 Creating directories..."
mkdir -p videos music sounds quotes output .tmp templates
echo "✓ Directories ready"

# Check for media files
VIDEO_COUNT=$(find videos -type f \( -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.mkv" \) 2>/dev/null | wc -l | tr -d ' ')
MUSIC_COUNT=$(find music -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.m4a" \) 2>/dev/null | wc -l | tr -d ' ')
QUOTE_COUNT=$(find quotes -type f -name "*.txt" 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo "📊 Media Files Status:"
echo "   Videos: $VIDEO_COUNT file(s)"
echo "   Music:  $MUSIC_COUNT file(s)"
echo "   Quotes: $QUOTE_COUNT file(s)"
echo ""

if [ "$VIDEO_COUNT" -eq 0 ]; then
    echo "⚠️  No video files found in videos/ directory"
    echo "   Add some .mp4, .mov, .avi, or .mkv files to get started"
    echo ""
fi

# Set default port
PORT=${PORT:-5000}

echo "🚀 Starting Web Server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   🌐 Open your browser and navigate to:"
echo "   "
echo "       http://localhost:$PORT"
echo "   "
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the web server
PORT=$PORT $PYTHON_CMD web_server.py
