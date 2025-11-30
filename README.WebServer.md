# Web Server Mode

The YouTube Video Builder includes a web interface for easy configuration and job management.

## Features

- 🎨 **Beautiful Web UI** - Modern, responsive interface
- ⚙️ **Visual Configuration** - Set all parameters through forms
- 📊 **Real-time Progress** - Watch your builds in real-time
- 📋 **Job Management** - Queue multiple builds, track status
- ⬇️ **Easy Downloads** - Download completed videos directly
- 🔄 **Background Processing** - Jobs run asynchronously
- 📁 **Media Browser** - See available videos, music, quotes

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Web Server

```bash
python web_server.py
```

The server will start at `http://localhost:5000`

### 3. Open Your Browser

Navigate to `http://localhost:5000` and start building videos!

## Configuration Options

### Environment Variables

```bash
# Server port (default: 5000)
PORT=5000

# Debug mode (default: true)
DEBUG=true

# Secret key for sessions (change in production!)
SECRET_KEY=your-secret-key-here
```

### Running on Custom Port

```bash
PORT=8080 python web_server.py
```

## Using the Web Interface

### 1. Configuration Panel (Left Side)

Configure all video parameters:

- **Duration** - Total video length in seconds
- **Resolution** - Choose from 720p, 1080p, or 4K
- **FPS** - Frame rate (24-60 fps)
- **Transition** - Crossfade, fade, or none
- **Quote Settings** - Duration and timing
- **Audio Levels** - Music and sound volume
- **Options** - Shuffle music/quotes, verbose logging

### 2. Jobs Panel (Right Side)

Track your builds:

- **Job Status** - Queued, Running, Completed, Failed
- **Progress Bar** - Real-time progress percentage
- **Current Step** - What's being processed
- **Actions** - Cancel running jobs, download completed videos

### 3. File Information

See how many media files are available:
- Video files in `videos/`
- Music files in `music/`
- Sound files in `sounds/`
- Quote files in `quotes/`

## API Endpoints

The web server exposes a REST API:

### Get Available Media Files
```bash
GET /api/files
```

### Create New Job
```bash
POST /api/jobs
Content-Type: application/json

{
  "duration": 600,
  "resolution": "1920x1080",
  "fps": 30,
  ...
}
```

### Get Job Status
```bash
GET /api/jobs/{job_id}
```

### Get Job Logs
```bash
GET /api/jobs/{job_id}/logs
```

### Cancel Job
```bash
POST /api/jobs/{job_id}/cancel
```

### List All Jobs
```bash
GET /api/jobs
```

### Download Output
```bash
GET /api/jobs/{job_id}/download
```

## Docker Usage

### Using Docker Compose with Web Server

```yaml
version: '3.8'

services:
  yt-builder-web:
    build: .
    container_name: yt-builder-web
    ports:
      - "5000:5000"
    volumes:
      - ./videos:/app/videos
      - ./music:/app/music
      - ./sounds:/app/sounds
      - ./quotes:/app/quotes
      - ./output:/app/output
    environment:
      PORT: "5000"
      DEBUG: "false"
      SECRET_KEY: "change-this-in-production"
    command: ["python", "web_server.py"]
```

### Run with Docker

```bash
docker-compose up yt-builder-web
```

Then open `http://localhost:5000`

## Production Deployment

For production, use a production WSGI server like Gunicorn:

### Install Gunicorn

```bash
pip install gunicorn
```

### Run with Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 web_server:app
```

### Nginx Reverse Proxy Example

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
    }
}
```

## Troubleshooting

### Port Already in Use

```bash
# Find what's using the port
lsof -i :5000

# Kill the process or use a different port
PORT=8080 python web_server.py
```

### Jobs Not Starting

- Check that `yt-builder.py` is in the same directory
- Verify all media files are in correct directories
- Check file permissions

### Cannot Download Completed Videos

- Ensure `output/` directory exists and is writable
- Check job status shows `completed` with an `output_file`

## Security Notes

⚠️ **Important for Production:**

1. **Change the SECRET_KEY** - Don't use the default in production
2. **Use HTTPS** - Set up SSL/TLS with Nginx or Apache
3. **Firewall** - Restrict access to trusted IPs if needed
4. **File Upload** - Consider adding authentication if enabling uploads
5. **Resource Limits** - Set system limits for concurrent jobs

## Advanced: Custom Job Queue

The current implementation uses simple threading. For production:

- Consider using **Celery** for distributed task queue
- Use **Redis** for job state management
- Implement **rate limiting** to prevent abuse
- Add **user authentication** for multi-user support

## Examples

### Batch Processing with API

```python
import requests

jobs = []
for duration in [300, 600, 900]:
    config = {
        "duration": duration,
        "resolution": "1920x1080",
        "fps": 30,
        "transition": "crossfade",
        "music_shuffle": True,
        "quotes_shuffle": True
    }

    response = requests.post('http://localhost:5000/api/jobs', json=config)
    jobs.append(response.json()['job_id'])

# Check status
for job_id in jobs:
    status = requests.get(f'http://localhost:5000/api/jobs/{job_id}')
    print(f"Job {job_id}: {status.json()['status']}")
```

## Support

For issues or questions:
- Check the main README.md
- Review logs with `--verbose` flag
- Open an issue on GitHub
