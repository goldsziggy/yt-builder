# Quick Start Guide

Get started with YouTube Video Builder in 3 easy steps!

## Using Docker (Recommended - No Setup Required!)

### Step 1: Build the Image

```bash
make build
# or
docker-compose build
```

### Step 2: Add Your Media

```bash
# Add videos (required)
cp /path/to/your/video.mp4 videos/

# Add music (optional)
cp /path/to/your/music.mp3 music/

# Quotes are already included as examples!
```

### Step 3: Create Your Video

**Easy way with Makefile:**
```bash
# Quick test (30 seconds)
make test

# High quality test (1 minute)
make test-hq

# Custom video
make run ARGS='--duration 300 -o /app/output/my_video.mp4'
```

**Or use the helper script:**
```bash
./run-docker.sh --duration 60 \
                --quotes-duration 5 \
                --quotes-min-between 10 \
                --quotes-max-between 20 \
                -o /app/output/video.mp4
```

**Or use docker-compose directly:**
```bash
docker-compose run --rm yt-builder \
    --duration 60 \
    --quotes-duration 5 \
    --quotes-min-between 10 \
    --quotes-max-between 20 \
    -o /app/output/video.mp4
```

### Step 4: Get Your Video

```bash
ls -lh output/
```

Your video is ready in the `output/` directory!

## Using Native Python (Alternative)

### Step 1: Install Dependencies

```bash
# Install FFmpeg
brew install ffmpeg  # macOS
# or
sudo apt-get install ffmpeg  # Linux

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Add Your Media

Same as Docker method above.

### Step 3: Create Your Video

```bash
python yt-builder.py \
    --duration 60 \
    --quotes-duration 5 \
    --quotes-min-between 10 \
    --quotes-max-between 20 \
    -o output.mp4
```

## Common Commands

### With Makefile

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make test` | Quick 30-second test video |
| `make test-hq` | High quality 1-minute test |
| `make dry-run` | Preview configuration |
| `make shell` | Open container shell for debugging |
| `make clean` | Clean output and temp files |
| `make info` | Show system and media info |

### Manual Docker Commands

```bash
# Build
docker-compose build

# Run with custom args
docker-compose run --rm yt-builder --duration 300 -o /app/output/video.mp4

# Shell access
docker-compose run --rm --entrypoint /bin/bash yt-builder

# View logs
docker-compose logs
```

## Configuration Examples

### Relaxation Video (10 minutes)

```bash
make run ARGS='--duration 600 \
    --quotes-duration 7 \
    --quotes-min-between 30 \
    --quotes-max-between 60 \
    --quote-style bottom \
    --music-volume 0.5 \
    -o /app/output/relaxation.mp4'
```

### Motivational Video (5 minutes)

```bash
make run ARGS='--duration 300 \
    --quotes-shuffle \
    --quotes-duration 4 \
    --quotes-min-between 10 \
    --quotes-max-between 20 \
    --music-volume 0.8 \
    -o /app/output/motivation.mp4'
```

### Study Music (1 hour, no quotes)

```bash
make run ARGS='--duration 3600 \
    --quotes-min-between 999999 \
    --quotes-max-between 999999 \
    --music-shuffle \
    -o /app/output/study.mp4'
```

## Troubleshooting

### "No video files found"

Add videos to the `videos/` directory:
```bash
ls videos/  # Check what's there
cp /path/to/video.mp4 videos/
```

### "Docker not found"

Install Docker Desktop:
- macOS/Windows: https://www.docker.com/products/docker-desktop
- Linux: https://docs.docker.com/engine/install/

### Video takes too long to process

Try:
- Lower resolution: `--resolution 1280x720`
- Shorter duration for testing: `--duration 30`
- No transitions: `--transition none`

### Check if everything is working

```bash
make info
```

This shows:
- Docker version
- Images available
- Number of media files
- Disk usage

## Next Steps

- **Full documentation**: See [README.md](README.md)
- **Docker guide**: See [DOCKER.md](DOCKER.md)
- **Usage examples**: See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)
- **Project requirements**: See [PRD.md](PRD.md)

## Quick Tips

1. **Start small**: Test with `make test` first (30 seconds)
2. **Use dry-run**: Preview config with `make dry-run`
3. **Check files**: Run `make info` to see media counts
4. **Clean regularly**: Run `make clean` to free up space
5. **Get help**: Run `make help` or `./run-docker.sh` for usage

Happy video building! 🎬
