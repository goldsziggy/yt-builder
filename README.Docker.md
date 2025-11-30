# Docker Usage Guide

This guide explains how to use the YouTube Video Builder with Docker.

## Quick Start

### 1. Build the Docker Image

```bash
docker build -t yt-builder .
```

### 2. Run with Docker Compose (Recommended)

```bash
# Edit docker-compose.yml to configure your settings
docker-compose up
```

### 3. Or Run Directly with Docker

```bash
docker run --rm \
  -v $(pwd)/videos:/app/videos \
  -v $(pwd)/music:/app/music \
  -v $(pwd)/sounds:/app/sounds \
  -v $(pwd)/quotes:/app/quotes \
  -v $(pwd)/output:/app/output \
  -e YT_BUILDER_DURATION=600 \
  -e YT_BUILDER_VERBOSE=true \
  yt-builder
```

## Configuration

### Using Environment Variables

All configuration can be done through environment variables prefixed with `YT_BUILDER_`:

| Environment Variable | Type | Default | Description |
|---------------------|------|---------|-------------|
| `YT_BUILDER_DURATION` | float | *required* | Duration of output video in seconds |
| `YT_BUILDER_QUOTES_DURATION` | float | 5.0 | How long to show each quote |
| `YT_BUILDER_QUOTES_MIN_BETWEEN` | float | 10.0 | Minimum time between quotes |
| `YT_BUILDER_QUOTES_MAX_BETWEEN` | float | 30.0 | Maximum time between quotes |
| `YT_BUILDER_MUSIC_SHUFFLE` | bool | false | Shuffle music files |
| `YT_BUILDER_QUOTES_SHUFFLE` | bool | false | Shuffle quotes |
| `YT_BUILDER_OUTPUT` | string | output.mp4 | Output file path |
| `YT_BUILDER_FPS` | int | 30 | Frame rate |
| `YT_BUILDER_RESOLUTION` | string | 1920x1080 | Output resolution |
| `YT_BUILDER_TRANSITION` | string | crossfade | Transition effect (none/fade/crossfade) |
| `YT_BUILDER_MUSIC_VOLUME` | float | 0.7 | Music volume (0.0-1.0) |
| `YT_BUILDER_SOUNDS_VOLUME` | float | 0.5 | Sound effects volume (0.0-1.0) |
| `YT_BUILDER_QUOTE_STYLE` | string | centered | Quote style (minimal/centered/bottom/top) |
| `YT_BUILDER_VERBOSE` | bool | false | Enable detailed logging |
| `YT_BUILDER_DRY_RUN` | bool | false | Preview configuration only |

### Boolean Values

Boolean environment variables accept multiple formats:
- `true`, `1`, `yes`, `on` → true
- `false`, `0`, `no`, `off` → false

## Directory Structure

Mount these directories as volumes:

```
/app/videos    - Video clips (required)
/app/music     - Background music files (optional)
/app/sounds    - Sound effects (optional)
/app/quotes    - Quote text files (optional)
/app/output    - Generated video output
```

## Examples

### Example 1: Basic Usage with Docker Compose

```yaml
services:
  yt-builder:
    build: .
    volumes:
      - ./videos:/app/videos
      - ./output:/app/output
    environment:
      YT_BUILDER_DURATION: "300"
      YT_BUILDER_VERBOSE: "true"
```

### Example 2: Full Configuration

```bash
docker run --rm \
  -v $(pwd)/videos:/app/videos \
  -v $(pwd)/music:/app/music \
  -v $(pwd)/sounds:/app/sounds \
  -v $(pwd)/quotes:/app/quotes \
  -v $(pwd)/output:/app/output \
  -e YT_BUILDER_DURATION=600 \
  -e YT_BUILDER_MUSIC_SHUFFLE=true \
  -e YT_BUILDER_QUOTES_SHUFFLE=true \
  -e YT_BUILDER_RESOLUTION=3840x2160 \
  -e YT_BUILDER_FPS=60 \
  -e YT_BUILDER_TRANSITION=fade \
  -e YT_BUILDER_MUSIC_VOLUME=0.6 \
  -e YT_BUILDER_QUOTE_STYLE=bottom \
  -e YT_BUILDER_VERBOSE=true \
  yt-builder
```

### Example 3: Dry Run to Preview Configuration

```bash
docker-compose run --rm \
  -e YT_BUILDER_DRY_RUN=true \
  yt-builder
```

### Example 4: Using .env File

```bash
# Copy example file
cp .env.example .env

# Edit .env with your settings
nano .env

# Run with environment file
docker run --rm \
  -v $(pwd)/videos:/app/videos \
  -v $(pwd)/output:/app/output \
  --env-file .env \
  yt-builder
```

## Command-Line Override

You can still use command-line arguments to override environment variables:

```bash
docker-compose run --rm yt-builder --duration 1200 --verbose
```

Command-line arguments take precedence over environment variables.

## Troubleshooting

### Check FFmpeg Installation

```bash
docker run --rm yt-builder ffmpeg -version
```

### Interactive Shell

```bash
docker run --rm -it yt-builder /bin/bash
```

### View Logs

```bash
docker-compose logs -f
```

## Building for Production

```bash
# Build optimized image
docker build -t yt-builder:latest .

# Tag for registry
docker tag yt-builder:latest your-registry/yt-builder:latest

# Push to registry
docker push your-registry/yt-builder:latest
```
