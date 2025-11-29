# Usage Examples

This document provides practical examples for using the YouTube Video Builder.

## Prerequisites

1. Install FFmpeg (see README.md for instructions)
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

### Step 1: Add Your Content

1. **Add videos** - Place your video files in the `videos/` directory:
   ```bash
   cp /path/to/your/video1.mp4 videos/
   cp /path/to/your/video2.mp4 videos/
   ```

2. **Add music** (optional) - Place background music in the `music/` directory:
   ```bash
   cp /path/to/your/music.mp3 music/
   ```

3. **Add sounds** (optional) - Place sound effects in the `sounds/` directory:
   ```bash
   cp /path/to/your/ambient.mp3 sounds/
   ```

4. **Add quotes** (optional) - Example quotes are already provided in `quotes/`, or add your own:
   ```bash
   echo "Your inspirational quote here" > quotes/my_quote.txt
   ```

### Step 2: Create Your Video

**Simple 5-minute video:**
```bash
python yt-builder.py --duration 300 \
                      --quotes-duration 5 \
                      --quotes-min-between 10 \
                      --quotes-max-between 30
```

This creates `output.mp4` with:
- 5 minutes duration
- Quotes appear for 5 seconds
- Random intervals between quotes (10-30 seconds)

## Common Use Cases

### 1. Meditation/Relaxation Video (10 minutes)

```bash
python yt-builder.py \
    --duration 600 \
    --quotes-duration 7 \
    --quotes-min-between 30 \
    --quotes-max-between 60 \
    --quote-style bottom \
    --music-volume 0.5 \
    --sounds-volume 0.3 \
    --transition fade \
    --output meditation.mp4
```

### 2. Motivational Video (3 minutes)

```bash
python yt-builder.py \
    --duration 180 \
    --quotes-shuffle \
    --quotes-duration 4 \
    --quotes-min-between 5 \
    --quotes-max-between 15 \
    --quote-style centered \
    --music-volume 0.8 \
    --transition crossfade \
    --output motivation.mp4 \
    --verbose
```

### 3. Study/Focus Video (1 hour)

```bash
python yt-builder.py \
    --duration 3600 \
    --quotes-duration 3 \
    --quotes-min-between 120 \
    --quotes-max-between 300 \
    --quote-style top \
    --music-shuffle \
    --music-volume 0.6 \
    --sounds-volume 0.4 \
    --output study_session.mp4
```

### 4. Minimal Video (No Quotes)

```bash
python yt-builder.py \
    --duration 600 \
    --quotes-duration 0 \
    --quotes-min-between 999999 \
    --quotes-max-between 999999 \
    --music-volume 0.7 \
    --output no_quotes.mp4
```

Or simply remove/move all quote files:
```bash
mkdir quotes_backup
mv quotes/*.txt quotes_backup/
```

### 5. 4K High Quality Video

```bash
python yt-builder.py \
    --duration 300 \
    --resolution 3840x2160 \
    --fps 60 \
    --quotes-duration 5 \
    --quotes-min-between 15 \
    --quotes-max-between 30 \
    --output 4k_video.mp4 \
    --verbose
```

### 6. Preview Before Rendering

```bash
python yt-builder.py \
    --duration 600 \
    --quotes-duration 5 \
    --quotes-min-between 10 \
    --quotes-max-between 30 \
    --dry-run
```

This shows the configuration without actually rendering the video.

## Resolution Presets

Common resolutions you can use:

- **4K UHD**: `--resolution 3840x2160`
- **1080p Full HD**: `--resolution 1920x1080` (default)
- **720p HD**: `--resolution 1280x720`
- **480p SD**: `--resolution 854x480`
- **Square (Instagram)**: `--resolution 1080x1080`
- **Vertical (Stories)**: `--resolution 1080x1920`

## Tips and Tricks

### Faster Processing

For quicker test renders:
```bash
python yt-builder.py \
    --duration 30 \
    --resolution 1280x720 \
    --transition none \
    --quotes-duration 3 \
    --quotes-min-between 5 \
    --quotes-max-between 10 \
    --output test.mp4
```

### Debug Issues

Use `--verbose` to see detailed logs:
```bash
python yt-builder.py --duration 300 --verbose
```

### Different Quote Styles

Try different quote positions:

**Top overlay** (good for landscape videos):
```bash
--quote-style top
```

**Bottom overlay** (subtitle style):
```bash
--quote-style bottom
```

**Centered** (default, most versatile):
```bash
--quote-style centered
```

**Minimal** (text only, no background):
```bash
--quote-style minimal
```

### Multiple Sound Layers

Each file in `sounds/` becomes an independent looping track:

```bash
sounds/
├── rain.mp3        # Rain ambience
├── birds.mp3       # Bird sounds
└── wind.mp3        # Wind sounds
```

All three will play simultaneously throughout the video!

### Randomize Everything

```bash
python yt-builder.py \
    --duration 600 \
    --music-shuffle \
    --quotes-shuffle \
    --quotes-duration 5 \
    --quotes-min-between 10 \
    --quotes-max-between 30 \
    --output random.mp4
```

## Troubleshooting

### "No video files found" error

Make sure you have video files in the `videos/` directory:
```bash
ls -la videos/
```

Supported formats: MP4, MOV, AVI, MKV

### Video processing is slow

This is normal for video encoding. Factors affecting speed:
- Higher resolution = slower
- Longer duration = slower
- More video clips = slower
- Crossfade transitions = slower than none

### Audio out of sync

If audio/video sync issues occur, try:
1. Ensure all input videos have similar frame rates
2. Use standard frame rates (24, 25, 30, 60)
3. Check that audio files are not corrupted

## Getting Help

For issues or questions:
1. Check the main README.md
2. Run with `--verbose` to see detailed logs
3. Try a `--dry-run` to verify configuration
4. Check that FFmpeg is installed: `ffmpeg -version`
