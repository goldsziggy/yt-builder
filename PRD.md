# Project Requirements Document

The goal of this project is the following: to provide an interface to create looping videos meant for Youtube.

The script will allow the following flags:

- DURATION: how long the video is
- MUSIC_SHUFFLE: (true|false, default: false) : Music in the music/ dir will be shuffled prior to the video launching.
- QUOTES_SHUFFLE: (true|false, default: false) : Quotes in the quotes/ dir will be shuffled prior to the video launching.
- QUOTES_DURATION: How long to show the quote on screen
- QUOTES_MIN_BETWEEN: minimum time till the next quote
- QUOTES_MAX_BETWEEN: maximum time till the next quote

# Structure

```
music/
videos/
quotes/
sounds/
```

Our script will take all of the videos in `videos/` and combine them and loop them for DURATION. This output will take the music in `music/` and loop them to completion as well. We will have a separate audio track for all files in sounds/. Each sound will be a separate looping track.

## Additional Flags/Options

- `--output` or `-o`: Output file path (default: `output.mp4` in current directory)
- `--fps`: Frame rate for output video (default: 30)
- `--resolution`: Output resolution in format WIDTHxHEIGHT (default: 1920x1080)
- `--music-volume`: Volume level for music track (0.0-1.0, default: 0.7)
- `--sounds-volume`: Volume level for sounds tracks (0.0-1.0, default: 0.5)
- `--quote-style`: Preset quote styling (minimal|centered|bottom|top, default: centered)
- `--transition`: Transition effect between video clips (none|fade|crossfade, default: crossfade)
- `--verbose`: Enable detailed logging output
- `--dry-run`: Preview configuration without rendering video

## Quote Display Specifications

### Quote File Format

- Quotes should be stored as text files (`.txt`) in the `quotes/` directory
- One quote per file
- Each file can contain multiple lines (will be displayed with line breaks)

### Quote Styling

- **Font**: Sans-serif, bold, large size (configurable via `--quote-style`)
- **Color**: White text with black outline/shadow for readability
- **Position**: Configurable (centered, bottom, top) via `--quote-style` flag
- **Background**: Optional semi-transparent overlay for better text visibility
- **Animation**: Fade in/out transitions when quotes appear/disappear
- **Text Wrapping**: Automatic wrapping for long quotes, max width 80% of screen

### Quote Timing

- Quotes appear for `QUOTES_DURATION` seconds
- Random interval between `QUOTES_MIN_BETWEEN` and `QUOTES_MAX_BETWEEN` before next quote
- Validation: `QUOTES_MIN_BETWEEN` must be <= `QUOTES_MAX_BETWEEN`

## Video Processing Specifications

### Supported Formats

- Input video formats: MP4, MOV, AVI, MKV
- Output format: MP4 (H.264 codec)

### Video Behavior

- **Resolution**: All input videos will be scaled/cropped to match `--resolution` setting
- **Aspect Ratio**: Maintained with letterboxing/pillarboxing as needed
- **Looping**: If combined video length < DURATION, loop from the beginning until DURATION is reached
- **Trimming**: If combined video length > DURATION, use first N clips that fit within DURATION
- **Transitions**: Configurable transition effects between clips (default: crossfade)

### Video Order

- Videos are processed in alphabetical order by filename
- If `MUSIC_SHUFFLE` is true, video order is randomized before processing

## Audio Mixing Specifications

### Music Track

- All music files in `music/` directory are combined and looped to match video DURATION
- If `MUSIC_SHUFFLE` is true, music files are shuffled before combining
- **Fade In/Out**: 2-second fade in at start, 2-second fade out at end
- **Crossfade**: If multiple music tracks, 1-second crossfade between tracks
- **Volume**: Controlled via `--music-volume` flag (default: 0.7)

### Sound Tracks

- Each file in `sounds/` directory becomes a separate looping audio track
- Sounds loop independently and continuously throughout the video
- **Volume**: Controlled via `--sounds-volume` flag (default: 0.5)
- **Synchronization**: Sounds start at video start and loop independently

### Audio Format Support

- Input formats: MP3, WAV, M4A, AAC, OGG
- Output: Mixed into single audio track in output video

## Output & Configuration

### Output File

- Default location: `output.mp4` in current directory
- Customizable via `--output` or `-o` flag
- Output format: MP4 with H.264 video codec and AAC audio codec

### Progress Indication

- Show progress bar during video processing
- Display current operation (combining videos, adding audio, rendering quotes, etc.)
- Estimated time remaining

### Logging

- Basic logging to console by default
- `--verbose` flag enables detailed logging including:
  - File processing details
  - Audio mixing information
  - Quote timing calculations
  - FFmpeg command details

## Edge Cases & Error Handling

### Input Validation

- Validate DURATION is a positive number
- Validate `QUOTES_MIN_BETWEEN` <= `QUOTES_MAX_BETWEEN`
- Validate volume levels are between 0.0 and 1.0
- Validate resolution format (WIDTHxHEIGHT)

### Empty Directories

- **Empty `videos/`**: Error - cannot create video without input videos
- **Empty `music/`**: Warning - video will be created without background music
- **Empty `quotes/`**: Warning - video will be created without quotes
- **Empty `sounds/`**: No warning - video will be created without sound effects

### File Format Issues

- **Unsupported formats**: Skip with warning, continue processing other files
- **Corrupted files**: Skip with error message, continue processing other files
- **Missing files**: Error if referenced file doesn't exist

### Resource Constraints

- Check available disk space before processing
- Estimate output file size and warn if insufficient space
- Handle memory constraints gracefully for large video files

## Technical Implementation Notes

### Recommended Libraries/Tools

- **FFmpeg**: For video/audio processing, encoding, and mixing
- **Pillow (PIL)**: For rendering quote text as images/overlays
- **pydub** or **moviepy**: For audio manipulation and mixing
- **argparse**: For command-line argument parsing
- **pathlib**: For file path handling

### Implementation Considerations

- Validate all inputs before starting processing
- Support both absolute and relative paths for directories
- Use temporary files for intermediate processing steps
- Clean up temporary files on completion or error
- Implement proper error handling and user-friendly error messages
- Consider parallel processing for multiple audio tracks if performance is an issue
