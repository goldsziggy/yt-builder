# Web Server with File Upload Feature

The YouTube Video Builder now supports file uploads through the web interface, with isolated run directories for each job.

## How It Works

### Architecture

Each job gets its own isolated directory structure:

```
runs/
└── run-1-a1b2c3d4/          # Unique run directory
    ├── videos/               # Video files for this run
    ├── music/                # Music files for this run
    ├── sounds/               # Sound files for this run
    ├── quotes/               # Quote files for this run
    ├── output/               # Output video location
    └── .tmp/                 # Temporary processing files
```

### Workflow

1. **Prepare Job** - Create job and run directory
2. **Upload Files** - Upload media files to the run directory
3. **Configure** - Set video parameters
4. **Start Job** - Begin processing
5. **Download** - Get the completed video

## API Endpoints

### 1. Prepare a New Job

```bash
POST /api/jobs/prepare

Response:
{
  "job_id": 1,
  "run_id": "run-1-a1b2c3d4",
  "status": "preparing"
}
```

### 2. Upload Files

```bash
POST /api/jobs/{job_id}/upload/{file_type}
Content-Type: multipart/form-data

file_type: videos | music | sounds | quotes
files: (multiple files)

Response:
{
  "uploaded": ["video1.mp4", "video2.mp4"],
  "errors": [],
  "file_counts": {
    "videos": 2,
    "music": 0,
    "sounds": 0,
    "quotes": 0
  }
}
```

### 2b. Download from Suno Playlist (Music Only)

```bash
POST /api/jobs/{job_id}/playlist/suno
Content-Type: application/json

{
  "url": "https://suno.com/playlist/abc123"
}

Response:
{
  "downloaded": ["song1.mp3", "song2.mp3"],
  "errors": [],
  "file_counts": {
    "videos": 0,
    "music": 2,
    "sounds": 0,
    "quotes": 0
  }
}
```

### 3. List Job Files

```bash
GET /api/jobs/{job_id}/files/{file_type}

Response:
{
  "files": ["video1.mp4", "video2.mp4"]
}
```

### 4. Delete a File

```bash
DELETE /api/jobs/{job_id}/files/{file_type}/{filename}

Response:
{
  "message": "File deleted",
  "file_counts": {...}
}
```

### 5. Start the Job

```bash
POST /api/jobs/{job_id}/start
Content-Type: application/json

{
  "duration": 600,
  "resolution": "1920x1080",
  "fps": 30,
  ...
}

Response:
{
  "job_id": 1,
  "status": "queued",
  ...
}
```

## Allowed File Types

### Videos
- `.mp4`, `.mov`, `.avi`, `.mkv`

### Audio (Music & Sounds)
- `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`

### Quotes
- `.txt`

## Environment Variables

The web server sets these environment variables for each job:

```bash
YT_BUILDER_VIDEOS_DIR=/path/to/runs/run-1-xxx/videos
YT_BUILDER_MUSIC_DIR=/path/to/runs/run-1-xxx/music
YT_BUILDER_SOUNDS_DIR=/path/to/runs/run-1-xxx/sounds
YT_BUILDER_QUOTES_DIR=/path/to/runs/run-1-xxx/quotes
YT_BUILDER_TEMP_DIR=/path/to/runs/run-1-xxx/.tmp
```

These variables tell `yt-builder.py` where to find media files for each specific run.

## Example: Using the API

### Python Example

```python
import requests

BASE_URL = 'http://localhost:5000/api'

# 1. Prepare a new job
response = requests.post(f'{BASE_URL}/jobs/prepare')
job_id = response.json()['job_id']
print(f"Created job #{job_id}")

# 2. Upload video files
with open('myvideo.mp4', 'rb') as f:
    files = {'files': f}
    response = requests.post(
        f'{BASE_URL}/jobs/{job_id}/upload/videos',
        files=files
    )
print(f"Uploaded: {response.json()['uploaded']}")

# 3. Upload music (manual upload)
with open('music.mp3', 'rb') as f:
    files = {'files': f}
    requests.post(
        f'{BASE_URL}/jobs/{job_id}/upload/music',
        files=files
    )

# OR download from Suno playlist
suno_response = requests.post(
    f'{BASE_URL}/jobs/{job_id}/playlist/suno',
    json={'url': 'https://suno.com/playlist/your-playlist-id'}
)
print(f"Downloaded {len(suno_response.json()['downloaded'])} songs from Suno")

# 4. Upload quotes
with open('quotes.txt', 'rb') as f:
    files = {'files': f}
    requests.post(
        f'{BASE_URL}/jobs/{job_id}/upload/quotes',
        files=files
    )

# 5. Start the job
config = {
    'duration': 300,
    'resolution': '1920x1080',
    'fps': 30,
    'transition': 'crossfade',
    'music_volume': 0.7,
    'sounds_volume': 0.5,
    'quote_style': 'centered'
}

response = requests.post(
    f'{BASE_URL}/jobs/{job_id}/start',
    json=config
)
print(f"Job started: {response.json()['status']}")

# 6. Monitor progress
import time
while True:
    response = requests.get(f'{BASE_URL}/jobs/{job_id}')
    status = response.json()
    print(f"Status: {status['status']} - {status['progress']}%")

    if status['status'] in ['completed', 'failed']:
        break

    time.sleep(2)

# 7. Download result
if status['status'] == 'completed':
    response = requests.get(f'{BASE_URL}/jobs/{job_id}/download')
    with open('output.mp4', 'wb') as f:
        f.write(response.content)
    print("Downloaded output.mp4")
```

### cURL Examples

```bash
# Prepare job
JOB_ID=$(curl -X POST http://localhost:5000/api/jobs/prepare | jq -r '.job_id')

# Upload video
curl -X POST \
  -F "files=@video.mp4" \
  http://localhost:5000/api/jobs/$JOB_ID/upload/videos

# Upload music (manual upload)
curl -X POST \
  -F "files=@music.mp3" \
  -F "files=@music2.mp3" \
  http://localhost:5000/api/jobs/$JOB_ID/upload/music

# OR download from Suno playlist
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://suno.com/playlist/your-playlist-id"}' \
  http://localhost:5000/api/jobs/$JOB_ID/playlist/suno

# Upload quotes
curl -X POST \
  -F "files=@quotes.txt" \
  http://localhost:5000/api/jobs/$JOB_ID/upload/quotes

# Start job
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "duration": 600,
    "resolution": "1920x1080",
    "fps": 30,
    "transition": "crossfade"
  }' \
  http://localhost:5000/api/jobs/$JOB_ID/start

# Check status
curl http://localhost:5000/api/jobs/$JOB_ID

# Download when complete
curl http://localhost:5000/api/jobs/$JOB_ID/download -o output.mp4
```

## Suno Playlist Integration

### 🎼 **Download Music from Suno**

Instead of manually uploading music files, you can provide a Suno playlist URL and the system will automatically download all songs from the playlist.

**Supported URL Formats:**
- `https://suno.com/playlist/{id}`
- `https://suno.com/@username/{playlist-id}`
- Any Suno URL containing `/playlist/`

**How It Works:**
1. Provide a Suno playlist URL
2. System fetches playlist metadata from Suno's API
3. Downloads all songs as MP3 files
4. Saves them to the job's music directory
5. Songs are immediately available for the video build

**Example:**
```bash
# Using the API
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://suno.com/playlist/abc123"}' \
  http://localhost:5000/api/jobs/1/playlist/suno

# Response
{
  "downloaded": ["Song-Title-1_abc12345.mp3", "Song-Title-2_def67890.mp3"],
  "errors": [],
  "file_counts": {
    "videos": 0,
    "music": 2,
    "sounds": 0,
    "quotes": 0
  }
}
```

**Using the Web Interface:**
1. Click "Upload New Files"
2. In the Music section, paste your Suno playlist URL
3. Click "Retrieve" button
4. Wait for download to complete
5. Songs will appear in the music file list

**Notes:**
- Downloads are saved with format: `{song-title}_{song-id}.mp3`
- Duplicate songs in playlists will overwrite previous downloads
- Large playlists may take several minutes to download
- Failed downloads are reported in the errors array

## Benefits

### 🔒 **Isolation**
Each job has its own files - no conflicts between concurrent jobs

### 📦 **Organization**
Easy to see what files were used for each video

### 🧹 **Cleanup**
Delete old run directories when done

### 👥 **Multi-User**
Multiple users can upload different files simultaneously

### 📊 **Tracking**
Each run is self-contained and reproducible

### 🎵 **Suno Integration**
Quickly add music from Suno playlists without manual downloads

## Cleanup

Run directories persist after job completion. To clean up:

```bash
# Remove a specific run
rm -rf runs/run-1-a1b2c3d4

# Remove all completed runs older than 7 days
find runs -type d -name "run-*" -mtime +7 -exec rm -rf {} +

# Keep only the 10 most recent runs
ls -t runs | tail -n +11 | xargs -I {} rm -rf runs/{}
```

## File Size Limits

Configure max upload size in Flask (web_server.py):

```python
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB
```

## Security Considerations

1. **Filename Sanitization** - Uses `secure_filename()` to prevent path traversal
2. **File Type Validation** - Only allows specific extensions
3. **Size Limits** - Configure max upload size
4. **Isolated Directories** - Each job has its own isolated space
5. **No Execute Permissions** - Uploaded files are data only

## Next Steps

See the web interface for a visual way to:
- Create jobs
- Upload files with drag-and-drop
- Monitor progress
- Download results

The UI handles all API calls automatically!
