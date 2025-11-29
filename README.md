# YouTube Video Builder

A Python tool for creating looping videos for YouTube with background music, sound effects, and text quote overlays.

## Features

- Combine and loop multiple video clips
- Add background music with fade in/out effects
- Layer multiple looping sound effects
- Overlay text quotes at random intervals
- Configurable transitions, resolution, and styling
- Progress tracking and detailed logging

## Quick Start with Docker (Recommended)

The easiest way to use this tool is with Docker, which includes all dependencies pre-installed:

```bash
# 1. Build the Docker image
docker-compose build

# 2. Add your media files to the directories
cp /path/to/videos/* videos/
cp /path/to/music/* music/

# 3. Run the tool
docker-compose run --rm yt-builder \
    --duration 60 \
    --quotes-duration 5 \
    --quotes-min-between 10 \
    --quotes-max-between 20 \
    -o /app/output/video.mp4

# 4. Find your video in the output/ directory
ls -lh output/
```

**See [DOCKER.md](DOCKER.md) for complete Docker usage guide.**

## Prerequisites (Native Installation)

### FFmpeg Installation

This tool requires FFmpeg to be installed on your system:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

### Python Dependencies

```bash
pip install -r requirements.txt
```

## Directory Structure

Create the following directories in your project folder:

```
yt-builder/
├── videos/     # Place your video files here (MP4, MOV, AVI, MKV)
├── music/      # Background music files (MP3, WAV, M4A, AAC, OGG)
├── quotes/     # Text files with quotes (one quote per file)
└── sounds/     # Sound effect files (MP3, WAV, M4A, AAC, OGG)
```

## Usage

### Basic Example

Create a 10-minute (600 second) video:

```bash
python yt-builder.py --duration 600 \
                      --quotes-duration 5 \
                      --quotes-min-between 10 \
                      --quotes-max-between 30
```

### Advanced Example

With all options:

```bash
python yt-builder.py \
    --duration 300 \
    --music-shuffle \
    --quotes-shuffle \
    --quotes-duration 7 \
    --quotes-min-between 15 \
    --quotes-max-between 45 \
    --output my_video.mp4 \
    --fps 30 \
    --resolution 1920x1080 \
    --music-volume 0.6 \
    --sounds-volume 0.4 \
    --quote-style centered \
    --transition crossfade \
    --verbose
```

### Dry Run

Preview configuration without rendering:

```bash
python yt-builder.py --duration 300 \
                      --quotes-duration 5 \
                      --quotes-min-between 10 \
                      --quotes-max-between 30 \
                      --dry-run
```

## Command-Line Options

### Required Arguments

- `--duration SECONDS` - Total duration of the output video

### Quote Options

- `--quotes-duration SECONDS` - How long each quote appears (default: 5.0)
- `--quotes-min-between SECONDS` - Minimum time between quotes (default: 10.0)
- `--quotes-max-between SECONDS` - Maximum time between quotes (default: 30.0)
- `--quotes-shuffle` - Randomize quote order

### Shuffle Options

- `--music-shuffle` - Shuffle music files before combining
- `--quotes-shuffle` - Shuffle quote files before displaying

### Output Options

- `-o, --output PATH` - Output file path (default: output.mp4)
- `--fps FPS` - Frame rate (default: 30)
- `--resolution WIDTHxHEIGHT` - Video resolution (default: 1920x1080)

### Audio Options

- `--music-volume LEVEL` - Music volume (0.0-1.0, default: 0.7)
- `--sounds-volume LEVEL` - Sound effects volume (0.0-1.0, default: 0.5)

### Visual Options

- `--quote-style STYLE` - Quote positioning: minimal, centered, bottom, top (default: centered)
- `--transition TYPE` - Transition effect: none, fade, crossfade (default: crossfade)

### Utility Options

- `--verbose` - Enable detailed logging
- `--dry-run` - Preview configuration without rendering

## Quote Files

Quotes should be stored as `.txt` files in the `quotes/` directory:

- One quote per file
- Multi-line quotes are supported
- UTF-8 encoding recommended
- Text will automatically wrap to fit 80% of screen width

**Example quote file** (`quotes/inspiration1.txt`):
```
Success is not final,
failure is not fatal:
it is the courage to continue that counts.
```

## How It Works

1. **Video Processing**: Combines all videos from `videos/` directory, loops them to match the target duration, and applies transitions
2. **Audio Mixing**: Combines music files (with crossfade), creates looping sound tracks, and mixes them together
3. **Quote Rendering**: Generates timed overlays for quotes with fade in/out effects
4. **Final Composition**: Combines video, audio, and quote overlays into the final MP4 file

## Video Processing Details

- Videos are concatenated in alphabetical order (or shuffled if `--music-shuffle` is enabled)
- If total video duration < target duration, videos loop from the beginning
- If total video duration > target duration, videos are trimmed to fit
- All videos are scaled to match the output resolution with letterboxing as needed

## Audio Processing Details

### Music Track
- All music files are combined and looped to match video duration
- 2-second fade in at start, 2-second fade out at end
- 1-second crossfade between tracks (if multiple files)
- Volume controlled via `--music-volume`

### Sound Tracks
- Each sound file becomes a separate looping track
- All sound tracks loop independently throughout the video
- Volume controlled via `--sounds-volume`

## Error Handling

The tool handles various edge cases:

- **Empty directories**:
  - `videos/` - Error (required)
  - `music/` - Warning (video created without music)
  - `quotes/` - Warning (video created without quotes)
  - `sounds/` - Silent (video created without sound effects)

- **Corrupted files**: Skipped with warning
- **Unsupported formats**: Skipped with warning
- **Disk space**: Checked before processing begins

## Performance Tips

- Use `--dry-run` to verify configuration before processing
- Lower resolutions process faster (e.g., 1280x720 vs 1920x1080)
- Use `none` transition for fastest processing
- Keep video files in a supported format (MP4 recommended)

## Troubleshooting

### "FFmpeg not found" error
Make sure FFmpeg is installed and available in your PATH.

### Slow processing
Video encoding is CPU-intensive. Consider:
- Using a lower resolution
- Reducing FPS (24 or 25 instead of 30)
- Using fewer video clips

### Out of disk space
The tool estimates output size but may need additional temporary space. Ensure you have at least 2-3x the estimated output size available.

### Quotes not appearing
Check that:
- Quote files are `.txt` format
- Quote timing allows them to fit within video duration
- Quote style is appropriate for your resolution

## License

This project is provided as-is for creating YouTube videos.

## Contributing

Feel free to submit issues or pull requests for improvements!
