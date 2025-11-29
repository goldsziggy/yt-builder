# Docker Usage Guide

This guide explains how to use the YouTube Video Builder with Docker.

## Why Docker?

Docker provides:
- **No manual setup** - FFmpeg and all dependencies are pre-installed
- **Consistent environment** - Works the same on any system
- **Isolation** - Doesn't affect your system
- **Easy cleanup** - Remove the container when done

## Prerequisites

Install Docker:
- **macOS/Windows**: [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Linux**: [Docker Engine](https://docs.docker.com/engine/install/)

## Quick Start

### Method 1: Using Docker Compose (Recommended)

1. **Add your media files**:
   ```bash
   cp /path/to/videos/* videos/
   cp /path/to/music/* music/
   # quotes/ already has examples
   ```

2. **Build the Docker image**:
   ```bash
   docker-compose build
   ```

3. **Run the tool**:
   ```bash
   docker-compose run --rm yt-builder \
       --duration 60 \
       --quotes-duration 5 \
       --quotes-min-between 10 \
       --quotes-max-between 20 \
       -o /app/output/test.mp4 \
       --verbose
   ```

4. **Find your output**:
   ```bash
   ls -lh output/
   ```

### Method 2: Using Docker Directly

1. **Build the image**:
   ```bash
   docker build -t yt-builder:latest .
   ```

2. **Run the container**:
   ```bash
   docker run --rm \
       -v "$(pwd)/videos:/app/videos:ro" \
       -v "$(pwd)/music:/app/music:ro" \
       -v "$(pwd)/quotes:/app/quotes:ro" \
       -v "$(pwd)/sounds:/app/sounds:ro" \
       -v "$(pwd)/output:/app/output" \
       yt-builder:latest \
       --duration 60 \
       --quotes-duration 5 \
       --quotes-min-between 10 \
       --quotes-max-between 20 \
       -o /app/output/test.mp4
   ```

## Common Commands

### Build the Image

```bash
# Using docker-compose
docker-compose build

# Using docker directly
docker build -t yt-builder:latest .
```

### Run with Different Options

**Dry run to preview configuration**:
```bash
docker-compose run --rm yt-builder \
    --duration 300 \
    --quotes-duration 5 \
    --quotes-min-between 10 \
    --quotes-max-between 30 \
    --dry-run
```

**Create a 5-minute video with verbose logging**:
```bash
docker-compose run --rm yt-builder \
    --duration 300 \
    --quotes-duration 7 \
    --quotes-min-between 15 \
    --quotes-max-between 45 \
    --music-shuffle \
    --quotes-shuffle \
    -o /app/output/my_video.mp4 \
    --verbose
```

**High-quality 1080p video**:
```bash
docker-compose run --rm yt-builder \
    --duration 600 \
    --resolution 1920x1080 \
    --fps 30 \
    --music-volume 0.7 \
    --sounds-volume 0.5 \
    --quote-style centered \
    -o /app/output/hq_video.mp4
```

**4K video** (requires more processing time):
```bash
docker-compose run --rm yt-builder \
    --duration 300 \
    --resolution 3840x2160 \
    --fps 60 \
    -o /app/output/4k_video.mp4
```

### Shell Access

To get a shell inside the container for debugging:

```bash
# Using docker-compose
docker-compose run --rm --entrypoint /bin/bash yt-builder

# Using docker directly
docker run --rm -it \
    -v "$(pwd)/videos:/app/videos:ro" \
    -v "$(pwd)/music:/app/music:ro" \
    -v "$(pwd)/quotes:/app/quotes:ro" \
    -v "$(pwd)/sounds:/app/sounds:ro" \
    -v "$(pwd)/output:/app/output" \
    --entrypoint /bin/bash \
    yt-builder:latest
```

Once inside, you can run commands manually:
```bash
python yt-builder.py --help
ffmpeg -version
ls -la videos/
```

## Directory Mapping

The docker-compose.yml maps these directories:

| Host Directory | Container Directory | Purpose | Access |
|---------------|---------------------|---------|--------|
| `./videos/` | `/app/videos/` | Input videos | Read-only |
| `./music/` | `/app/music/` | Background music | Read-only |
| `./quotes/` | `/app/quotes/` | Quote text files | Read-only |
| `./sounds/` | `/app/sounds/` | Sound effects | Read-only |
| `./output/` | `/app/output/` | Generated videos | Read-write |
| `./.tmp/` | `/app/.tmp/` | Temporary files | Read-write |

## Best Practices

### 1. Use the output directory

Always output to `/app/output/` in the container:
```bash
-o /app/output/my_video.mp4
```

This maps to `./output/my_video.mp4` on your host system.

### 2. Clean up temporary files

The `.tmp/` directory can grow large. Clean it periodically:
```bash
rm -rf .tmp/*
```

### 3. Resource limits

For large videos, you may want to adjust Docker's resource limits:

Edit `docker-compose.yml` and uncomment the `deploy` section:
```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

### 4. Pre-pull the base image

Speed up builds by pre-pulling the Python image:
```bash
docker pull python:3.11-slim
```

## Troubleshooting

### Container fails to start

Check Docker is running:
```bash
docker info
```

### Permission errors

If you get permission errors on Linux, ensure your user owns the directories:
```bash
sudo chown -R $USER:$USER videos/ music/ quotes/ sounds/ output/ .tmp/
```

### Out of disk space

Check Docker disk usage:
```bash
docker system df
```

Clean up unused images and containers:
```bash
docker system prune -a
```

### Video processing is slow

Docker adds minimal overhead, but ensure:
1. Docker has enough CPU/memory allocated (check Docker Desktop settings)
2. Your input files are not excessively large
3. You're not using too high a resolution for testing

### Can't find output file

Make sure you're outputting to `/app/output/`:
```bash
-o /app/output/video.mp4  # Correct
-o /app/video.mp4          # Wrong - will be inside container only
```

## Advanced Usage

### Custom Dockerfile

To modify the Docker image, edit the `Dockerfile`:

```dockerfile
# Add additional fonts
RUN apt-get update && apt-get install -y fonts-noto

# Install additional Python packages
RUN pip install my-package
```

Then rebuild:
```bash
docker-compose build --no-cache
```

### Using with CI/CD

Example GitHub Actions workflow:

```yaml
name: Build Video

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build video
        run: |
          docker-compose build
          docker-compose run --rm yt-builder \
            --duration 300 \
            --quotes-duration 5 \
            --quotes-min-between 10 \
            --quotes-max-between 30 \
            -o /app/output/automated_video.mp4

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: video
          path: output/automated_video.mp4
```

### Multi-stage builds

The Dockerfile uses a single stage, but you could optimize it with multi-stage builds for smaller images.

## Comparison: Docker vs Native

| Aspect | Docker | Native |
|--------|--------|--------|
| Setup time | Fast (docker-compose up) | Slow (install FFmpeg, deps) |
| Disk usage | ~500MB image | ~100MB |
| Performance | Near-native | Native |
| Portability | High (works anywhere) | Low (OS-specific) |
| Cleanup | Easy (docker rmi) | Manual |

## Updating

To update to a new version:

```bash
# Rebuild the image
docker-compose build --no-cache

# Or pull if using a registry
docker pull yt-builder:latest
```

## Removing Docker Resources

When you're done:

```bash
# Remove the image
docker rmi yt-builder:latest

# Remove containers
docker-compose down

# Remove all unused Docker resources
docker system prune -a
```

## Support

For Docker-specific issues:
1. Check Docker logs: `docker-compose logs`
2. Verify mounts: `docker-compose config`
3. Test with shell access: `docker-compose run --rm --entrypoint /bin/bash yt-builder`

For application issues, see the main README.md.
