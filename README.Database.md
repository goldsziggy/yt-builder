# Database Integration

The YouTube Video Builder uses SQLite to persist job data, track files, and maintain history across server restarts.

## Database Location

The database file is stored at:
```
./data/yt-builder.db
```

This directory is automatically created on first run.

## Database Schema

### Tables

#### 1. `jobs`
Tracks all video build jobs.

| Column | Type | Description |
|--------|------|-------------|
| job_id | INTEGER | Primary key, unique job identifier |
| run_id | TEXT | Human-readable run identifier (e.g., `run-1-abc123`) |
| run_dir | TEXT | Path to job's run directory |
| status | TEXT | Job status: `preparing`, `queued`, `running`, `completed`, `failed`, `cancelled` |
| progress | INTEGER | Progress percentage (0-100) |
| current_step | TEXT | Current processing step |
| config | TEXT | JSON-encoded job configuration |
| output_file | TEXT | Path to output video file |
| error | TEXT | Error message if job failed |
| created_at | TEXT | ISO timestamp when job was created |
| started_at | TEXT | ISO timestamp when job started processing |
| finished_at | TEXT | ISO timestamp when job finished |

**Indexes:**
- `idx_jobs_status` on `status`
- `idx_jobs_created` on `created_at DESC`

#### 2. `job_files`
Tracks uploaded files for each job.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| job_id | INTEGER | Foreign key to `jobs.job_id` |
| file_type | TEXT | File type: `videos`, `music`, `sounds`, `quotes` |
| filename | TEXT | Original filename |
| file_path | TEXT | Full path to file |
| uploaded_at | TEXT | ISO timestamp when file was uploaded |

**Indexes:**
- `idx_job_files_job` on `job_id`

**Constraints:**
- Unique constraint on `(job_id, file_type, filename)`
- ON DELETE CASCADE with `jobs` table

#### 3. `youtube_uploads`
Records YouTube upload history.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| job_id | INTEGER | Foreign key to `jobs.job_id` |
| video_id | TEXT | YouTube video ID |
| video_url | TEXT | Full YouTube URL |
| title | TEXT | Video title |
| description | TEXT | Video description |
| privacy | TEXT | Privacy setting: `private`, `unlisted`, `public` |
| tags | TEXT | JSON array of tags |
| category | TEXT | YouTube category ID |
| uploaded_at | TEXT | ISO timestamp when uploaded |

**Indexes:**
- `idx_youtube_job` on `job_id`

**Constraints:**
- ON DELETE CASCADE with `jobs` table

## Features

### Automatic Persistence
- All job state changes are automatically saved to the database
- File uploads are tracked in the database
- YouTube uploads are recorded with full metadata

### Server Restart Recovery
- Jobs are loaded from database on server startup
- Preparing/queued jobs are restored to memory
- Completed jobs remain queryable in history

### File Tracking
- Every uploaded file is tracked with metadata
- File counts are calculated from database (not filesystem)
- Supports file deletion tracking

### YouTube Upload History
- Complete record of all YouTube uploads
- Includes video metadata and upload timestamps
- Linked to original job for traceability

## API Integration

The database is transparently integrated with the web API:

### Job Creation
```python
# Prepare new job
job_id = db.get_next_job_id()
db.create_job(job_id, run_id, run_dir, config)
```

### Status Updates
```python
# Update job status
job.update_status('running', progress=50, current_step='Mixing audio')
# Automatically syncs to database
```

### File Tracking
```python
# Track uploaded file
db.add_file(job_id, 'videos', 'video.mp4', '/path/to/video.mp4')

# Get file counts
counts = db.get_file_counts(job_id)
# Returns: {'videos': 2, 'music': 1, 'sounds': 0, 'quotes': 1}
```

### YouTube Uploads
```python
# Record YouTube upload
db.add_youtube_upload(
    job_id=1,
    video_id='dQw4w9WgXcQ',
    video_url='https://youtube.com/watch?v=dQw4w9WgXcQ',
    title='My Video',
    description='Description',
    privacy='private',
    tags=['tag1', 'tag2'],
    category='22'
)
```

## Database Methods

### Job Management

```python
# Get next available job ID
job_id = db.get_next_job_id()

# Create new job
db.create_job(job_id, run_id, run_dir, config)

# Get job by ID
job_data = db.get_job(job_id)

# Get all jobs (newest first)
jobs = db.get_all_jobs(limit=100)

# Update job status
db.update_job_status(
    job_id,
    status='completed',
    progress=100,
    output_file='/path/to/output.mp4'
)

# Update job configuration
db.update_job_config(job_id, new_config)
```

### File Tracking

```python
# Add file
db.add_file(job_id, 'videos', 'video.mp4', '/path/to/file')

# Get files for job
files = db.get_job_files(job_id, file_type='videos')

# Delete file tracking
db.delete_file(job_id, 'videos', 'video.mp4')

# Get file counts
counts = db.get_file_counts(job_id)
```

### YouTube History

```python
# Add YouTube upload
db.add_youtube_upload(job_id, video_id, video_url, title, description, privacy, tags, category)

# Get uploads for job
uploads = db.get_youtube_uploads(job_id=1)

# Get all recent uploads
all_uploads = db.get_youtube_uploads()
```

### Maintenance

```python
# Cleanup old completed jobs
deleted_count = db.cleanup_old_jobs(days=30)
```

## Data Retention

### Automatic Cleanup

You can periodically clean up old jobs:

```python
# Delete jobs completed more than 30 days ago
db.cleanup_old_jobs(days=30)
```

### Manual Cleanup

```bash
# Delete jobs older than 60 days
python -c "from src.database import Database; db = Database(); print(f'Deleted {db.cleanup_old_jobs(60)} jobs')"
```

## Backup & Recovery

### Backup

```bash
# Simple backup
cp data/yt-builder.db data/yt-builder-backup-$(date +%Y%m%d).db

# Compressed backup
sqlite3 data/yt-builder.db ".backup data/backup.db"
gzip data/backup.db
```

### Restore

```bash
# Restore from backup
cp data/yt-builder-backup-20250101.db data/yt-builder.db

# Restart server to reload
```

## Database Queries

You can query the database directly using `sqlite3`:

```bash
# Open database
sqlite3 data/yt-builder.db

# List all tables
.tables

# Show schema
.schema jobs

# Query jobs
SELECT job_id, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;

# Get completed jobs count
SELECT COUNT(*) FROM jobs WHERE status = 'completed';

# Get total files uploaded
SELECT file_type, COUNT(*) FROM job_files GROUP BY file_type;

# Get YouTube upload stats
SELECT COUNT(*) as uploads, privacy, COUNT(DISTINCT job_id) as unique_jobs
FROM youtube_uploads
GROUP BY privacy;
```

## Migration & Schema Updates

The database schema is automatically created on first run. Future schema updates will be handled via migrations (to be implemented).

### Current Version
- Schema version: 1.0
- Created: 2025

## Performance Considerations

### Indexes
All frequently-queried columns have indexes:
- Job status lookups
- Job creation time sorting
- File lookups by job_id
- YouTube upload lookups

### Connection Pooling
Each request uses a new connection with context manager for safety.

### Transaction Safety
All write operations are wrapped in transactions for atomicity.

## Environment Variables

```bash
# Custom database location
export YT_BUILDER_DB_PATH=/custom/path/database.db
```

Update `web_server.py`:
```python
db_path = os.environ.get('YT_BUILDER_DB_PATH', 'data/yt-builder.db')
db = Database(db_path)
```

## Troubleshooting

### Database Locked

If you get "database is locked" errors:
- Ensure only one web server instance is running
- Check for long-running queries
- Increase timeout in database.py

### Corrupted Database

```bash
# Check integrity
sqlite3 data/yt-builder.db "PRAGMA integrity_check;"

# Recover if possible
sqlite3 data/yt-builder.db ".recover" | sqlite3 recovered.db
```

### Reset Database

```bash
# Backup first!
cp data/yt-builder.db data/yt-builder-old.db

# Delete database (will be recreated on next start)
rm data/yt-builder.db

# Restart server
python web_server.py
```

## Example: Query Job History

```python
from src.database import Database

db = Database()

# Get all completed jobs from last 7 days
from datetime import datetime, timedelta

cutoff = (datetime.now() - timedelta(days=7)).isoformat()
jobs = db.get_all_jobs()

recent_completed = [
    j for j in jobs
    if j['status'] == 'completed' and j['created_at'] > cutoff
]

for job in recent_completed:
    print(f"Job #{job['job_id']}: {job['run_id']}")
    print(f"  Created: {job['created_at']}")
    print(f"  Output: {job['output_file']}")

    # Get YouTube uploads for this job
    uploads = db.get_youtube_uploads(job['job_id'])
    for upload in uploads:
        print(f"  YouTube: {upload['video_url']}")
```

## Benefits

### ✅ **Persistence**
All data survives server restarts

### 📊 **Analytics**
Query historical data for insights

### 🔍 **Traceability**
Track every file and upload

### 🔄 **Recovery**
Resume interrupted jobs

### 📈 **Scalability**
SQLite handles millions of records efficiently

### 🔒 **Reliability**
ACID transactions ensure data integrity
