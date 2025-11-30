#!/usr/bin/env python3
"""
Web Server for YouTube Video Builder
Provides a web interface for configuring and running video builds
"""

import os
import sys
import json
import queue
import shutil
import subprocess
import threading
import uuid
import re
import requests
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from database import Database

# YouTube API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    print("Warning: YouTube API libraries not installed. YouTube upload will be disabled.")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Configuration
RUNS_DIR = Path('runs')
RUNS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    'video': {'.mp4', '.mov', '.avi', '.mkv'},
    'audio': {'.mp3', '.wav', '.m4a', '.aac', '.ogg'},
    'quote': {'.txt'}
}

# Initialize database
db = Database('data/yt-builder.db')

# Job management
jobs = {}
job_lock = threading.Lock()


def allowed_file(filename, file_type):
    """Check if file extension is allowed for the given type"""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS.get(file_type, set())


class Job:
    """Represents a video build job"""

    def __init__(self, job_id, config, run_dir, run_id=None):
        self.job_id = job_id
        self.config = config
        self.run_dir = Path(run_dir) if isinstance(run_dir, str) else run_dir
        self.run_id = run_id or self.run_dir.name
        self.status = 'queued'
        self.progress = 0
        self.current_step = ''
        self.output_file = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.finished_at = None
        self.process = None
        self.log_queue = queue.Queue()

        # Create run directory structure
        self._create_run_directories()

    def _create_run_directories(self):
        """Create directory structure for this run"""
        self.videos_dir = self.run_dir / 'videos'
        self.music_dir = self.run_dir / 'music'
        self.sounds_dir = self.run_dir / 'sounds'
        self.quotes_dir = self.run_dir / 'quotes'
        self.output_dir = self.run_dir / 'output'
        self.temp_dir = self.run_dir / '.tmp'

        for directory in [self.videos_dir, self.music_dir, self.sounds_dir,
                         self.quotes_dir, self.output_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def get_file_counts(self):
        """Get count of files in each directory"""
        # Get from database for accuracy
        return db.get_file_counts(self.job_id)

    def update_status(self, status, **kwargs):
        """Update job status in database"""
        self.status = status

        if 'progress' in kwargs:
            self.progress = kwargs['progress']
        if 'current_step' in kwargs:
            self.current_step = kwargs['current_step']
        if 'output_file' in kwargs:
            self.output_file = kwargs['output_file']
        if 'error' in kwargs:
            self.error = kwargs['error']

        if status == 'running' and not self.started_at:
            self.started_at = datetime.now()

        if status in ['completed', 'failed', 'cancelled']:
            self.finished_at = datetime.now()

        # Update database
        db.update_job_status(
            self.job_id,
            status,
            progress=self.progress,
            current_step=self.current_step,
            output_file=self.output_file,
            error=self.error
        )

    def to_dict(self):
        """Convert job to dictionary for JSON serialization"""
        return {
            'job_id': self.job_id,
            'run_id': self.run_id,
            'status': self.status,
            'progress': self.progress,
            'current_step': self.current_step,
            'output_file': self.output_file,
            'error': self.error,
            'file_counts': self.get_file_counts(),
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }

    @staticmethod
    def from_db(job_data):
        """Create Job instance from database data"""
        job = Job(
            job_id=job_data['job_id'],
            config=job_data['config'],
            run_dir=job_data['run_dir'],
            run_id=job_data['run_id']
        )
        job.status = job_data['status']
        job.progress = job_data['progress']
        job.current_step = job_data['current_step'] or ''
        job.output_file = job_data['output_file']
        job.error = job_data['error']

        # Parse timestamps
        if job_data['created_at']:
            job.created_at = datetime.fromisoformat(job_data['created_at'])
        if job_data['started_at']:
            job.started_at = datetime.fromisoformat(job_data['started_at'])
        if job_data['finished_at']:
            job.finished_at = datetime.fromisoformat(job_data['finished_at'])

        return job


def run_job(job):
    """Run a video build job in background"""
    job.update_status('running')

    # Build command
    cmd = ['python', 'yt-builder.py']

    # Add all parameters
    config = job.config
    cmd.extend(['--duration', str(config['duration'])])
    cmd.extend(['--quotes-duration', str(config['quotes_duration'])])
    cmd.extend(['--quotes-min-between', str(config['quotes_min_between'])])
    cmd.extend(['--quotes-max-between', str(config['quotes_max_between'])])
    cmd.extend(['--fps', str(config['fps'])])
    cmd.extend(['--resolution', config['resolution']])
    cmd.extend(['--transition', config['transition']])
    cmd.extend(['--music-volume', str(config['music_volume'])])
    cmd.extend(['--sounds-volume', str(config['sounds_volume'])])
    cmd.extend(['--quote-style', config['quote_style']])

    if config.get('music_shuffle'):
        cmd.append('--music-shuffle')
    if config.get('quotes_shuffle'):
        cmd.append('--quotes-shuffle')
    if config.get('verbose'):
        cmd.append('--verbose')

    # Output file in run directory
    output_filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    output_path = job.output_dir / output_filename
    cmd.extend(['-o', str(output_path)])

    # Set environment variables for run-specific directories
    env = os.environ.copy()
    env['YT_BUILDER_VIDEOS_DIR'] = str(job.videos_dir)
    env['YT_BUILDER_MUSIC_DIR'] = str(job.music_dir)
    env['YT_BUILDER_SOUNDS_DIR'] = str(job.sounds_dir)
    env['YT_BUILDER_QUOTES_DIR'] = str(job.quotes_dir)
    env['YT_BUILDER_TEMP_DIR'] = str(job.temp_dir)

    try:
        # Run the command with custom environment
        job.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            cwd=os.getcwd()
        )

        # Read output and update progress
        for line in iter(job.process.stdout.readline, ''):
            if not line:
                break

            # Parse progress from line
            job.log_queue.put(line.strip())

            # Update job status based on log lines
            if 'Step 1/4' in line:
                job.update_status('running', current_step='Processing video clips', progress=25)
            elif 'Step 2/4' in line:
                job.update_status('running', current_step='Mixing audio tracks', progress=50)
            elif 'Step 3/4' in line:
                job.update_status('running', current_step='Rendering quotes', progress=75)
            elif 'Step 4/4' in line:
                job.update_status('running', current_step='Creating final video', progress=90)
            elif 'Video successfully created' in line:
                job.update_status('running', current_step='Complete', progress=100)
            elif 'ERROR' in line:
                job.error = line

        return_code = job.process.wait()

        if return_code == 0:
            job.update_status('completed', output_file=str(output_path), progress=100)
        else:
            job.update_status('failed', error=f"Process exited with code {return_code}")

    except Exception as e:
        job.update_status('failed', error=str(e))


@app.route('/')
def index():
    """Main page with configuration form"""
    return render_template('index.html')


@app.route('/api/config/defaults')
def get_defaults():
    """Get default configuration values"""
    return jsonify({
        'duration': 600,
        'quotes_duration': 5.0,
        'quotes_min_between': 10.0,
        'quotes_max_between': 30.0,
        'fps': 30,
        'resolution': '1920x1080',
        'transition': 'crossfade',
        'music_volume': 0.7,
        'sounds_volume': 0.5,
        'quote_style': 'centered',
        'music_shuffle': False,
        'quotes_shuffle': False,
        'verbose': True
    })


@app.route('/api/files')
def list_files():
    """List available media files"""
    def get_files(directory, extensions):
        path = Path(directory)
        if not path.exists():
            return []
        files = []
        for ext in extensions:
            files.extend([f.name for f in path.glob(f'*{ext}')])
        return sorted(files)

    return jsonify({
        'videos': get_files('videos', ['.mp4', '.mov', '.avi', '.mkv']),
        'music': get_files('music', ['.mp3', '.wav', '.m4a', '.aac', '.ogg']),
        'sounds': get_files('sounds', ['.mp3', '.wav', '.m4a', '.aac', '.ogg']),
        'quotes': get_files('quotes', ['.txt'])
    })


@app.route('/api/jobs/<int:job_id>/upload/<file_type>', methods=['POST'])
def upload_files(job_id, file_type):
    """Upload files for a specific job"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if file_type not in ['videos', 'music', 'sounds', 'quotes']:
        return jsonify({'error': 'Invalid file type'}), 400

    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    uploaded_files = []
    errors = []

    # Determine target directory and allowed type
    target_dir = getattr(job, f'{file_type}_dir')
    allowed_type = 'video' if file_type == 'videos' else \
                   'audio' if file_type in ['music', 'sounds'] else 'quote'

    for file in files:
        if file.filename == '':
            continue

        if not allowed_file(file.filename, allowed_type):
            errors.append(f'{file.filename}: Invalid file type')
            continue

        try:
            filename = secure_filename(file.filename)
            filepath = target_dir / filename
            file.save(str(filepath))
            uploaded_files.append(filename)

            # Track in database
            db.add_file(job_id, file_type, filename, str(filepath))
        except Exception as e:
            errors.append(f'{file.filename}: {str(e)}')

    return jsonify({
        'uploaded': uploaded_files,
        'errors': errors,
        'file_counts': job.get_file_counts()
    })


@app.route('/api/jobs/<int:job_id>/files/<file_type>')
def list_job_files(job_id, file_type):
    """List files for a specific job"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if file_type not in ['videos', 'music', 'sounds', 'quotes']:
        return jsonify({'error': 'Invalid file type'}), 400

    directory = getattr(job, f'{file_type}_dir')
    files = [f.name for f in directory.glob('*.*') if f.is_file()]

    return jsonify({'files': sorted(files)})


@app.route('/api/jobs/<int:job_id>/files/<file_type>/<filename>', methods=['DELETE'])
def delete_job_file(job_id, file_type, filename):
    """Delete a file from a job"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if file_type not in ['videos', 'music', 'sounds', 'quotes']:
        return jsonify({'error': 'Invalid file type'}), 400

    directory = getattr(job, f'{file_type}_dir')
    filepath = directory / secure_filename(filename)

    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404

    try:
        filepath.unlink()

        # Delete from database
        db.delete_file(job_id, file_type, filename)

        return jsonify({
            'message': 'File deleted',
            'file_counts': job.get_file_counts()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def extract_playlist_id(url: str) -> str:
    """Extract playlist ID from various Suno URL formats"""
    # Try different URL patterns
    patterns = [
        r'/playlists/([a-zA-Z0-9_-]+)',
        r'/playlist/([a-zA-Z0-9_-]+)',
        r'\?id=([a-zA-Z0-9_-]+)',
        r'suno\.com/([a-zA-Z0-9_-]{10,})'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If no pattern matches, check if the URL itself might be the ID
    cleaned = url.strip().split('/')[-1].split('?')[0]
    if len(cleaned) >= 10 and re.match(r'^[a-zA-Z0-9_-]+$', cleaned):
        return cleaned

    return None


def fetch_suno_playlist_page(playlist_id: str, page: int = 0) -> dict:
    """Fetch a single page of a Suno playlist"""
    api_url = f'https://studio-api.prod.suno.com/api/playlist/{playlist_id}/'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://suno.com/'
    }

    params = {'page': page} if page > 0 else {}

    response = requests.get(api_url, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    return response.json()


def download_suno_playlist(playlist_url: str, output_dir: Path) -> dict:
    """
    Download songs from a Suno playlist.
    Returns dict with 'downloaded' list and 'errors' list.
    """
    downloaded = []
    errors = []

    try:
        # Extract playlist ID from URL
        playlist_id = extract_playlist_id(playlist_url)

        if not playlist_id:
            return {
                'downloaded': [],
                'errors': ['Invalid Suno playlist URL format. Please provide a valid Suno playlist URL.']
            }

        # Fetch all pages of the playlist
        all_clips = []
        seen_ids = set()
        page = 0

        while True:
            try:
                playlist_data = fetch_suno_playlist_page(playlist_id, page)

                # Get clips from this page
                clips = playlist_data.get('playlist_clips', [])

                if not clips:
                    break

                # Filter and deduplicate clips
                for clip_item in clips:
                    clip_data = clip_item.get('clip', {})
                    clip_id = clip_data.get('id')
                    audio_url = clip_data.get('audio_url')

                    # Only include clips with valid ID and audio URL
                    if clip_id and audio_url and clip_id not in seen_ids:
                        all_clips.append(clip_item)
                        seen_ids.add(clip_id)

                page += 1

                # Safety limit to prevent infinite loops
                if page > 100:
                    errors.append('Reached pagination limit (100 pages)')
                    break

            except requests.HTTPError as e:
                if page == 0:
                    # First page failed
                    return {
                        'downloaded': [],
                        'errors': [f'Failed to fetch playlist: HTTP {e.response.status_code}']
                    }
                else:
                    # Subsequent page failed, probably no more pages
                    break

        if not all_clips:
            return {
                'downloaded': [],
                'errors': ['No songs found in playlist or all clips are invalid']
            }

        # Download each song
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://suno.com/'
        }

        print(f"[Suno] Found {len(all_clips)} unique clips to download")

        for idx, clip in enumerate(all_clips):
            try:
                # Get clip metadata from the nested structure
                clip_data = clip.get('clip', {})

                song_title = clip_data.get('title', '').strip()
                song_id = clip_data.get('id', '')
                audio_url = clip_data.get('audio_url')

                # Skip if no audio URL (already filtered, but double-check)
                if not audio_url:
                    errors.append(f'Clip {idx + 1}: No audio URL found')
                    continue

                # Sanitize filename
                if song_title:
                    safe_title = re.sub(r'[^\w\s-]', '', song_title)
                    safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-')
                else:
                    safe_title = ''

                # Use fallback name if no title or sanitization resulted in empty string
                if not safe_title:
                    safe_title = f'Untitled-Song-{idx + 1}'
                    display_title = f'Untitled Song {idx + 1}'
                else:
                    display_title = song_title

                filename = f'{safe_title}_{song_id[:8]}.mp3' if song_id else f'{safe_title}.mp3'

                print(f"[Suno] Downloading {idx + 1}/{len(all_clips)}: {display_title}")

                # Download the song
                song_response = requests.get(audio_url, headers=headers, timeout=120, stream=True)
                song_response.raise_for_status()

                filepath = output_dir / filename

                with open(filepath, 'wb') as f:
                    for chunk in song_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                downloaded.append(filename)
                print(f"[Suno] ✓ Downloaded: {filename}")

                # Track in database if job_id is available (will be passed from endpoint)
                if hasattr(output_dir, 'parent') and 'runs' in str(output_dir):
                    # Extract job_id from path if possible - will be set by endpoint
                    pass

            except requests.HTTPError as e:
                song_title = clip.get('clip', {}).get('title', f'Unknown')
                error_msg = f'{song_title}: Download failed (HTTP {e.response.status_code})'
                errors.append(error_msg)
                print(f"[Suno] ✗ {error_msg}")
            except Exception as e:
                song_title = clip.get('clip', {}).get('title', f'Unknown')
                error_msg = f'{song_title}: {str(e)}'
                errors.append(error_msg)
                print(f"[Suno] ✗ {error_msg}")

    except requests.Timeout:
        errors.append('Request timeout - playlist may be too large or server is slow')
    except requests.RequestException as e:
        errors.append(f'Network error: {str(e)}')
    except Exception as e:
        errors.append(f'Unexpected error: {str(e)}')

    return {
        'downloaded': downloaded,
        'errors': errors
    }


@app.route('/api/jobs/<int:job_id>/playlist/suno', methods=['POST'])
def download_suno_playlist_endpoint(job_id):
    """Download songs from a Suno playlist URL"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    data = request.get_json()
    playlist_url = data.get('url', '').strip()

    if not playlist_url:
        return jsonify({'error': 'Playlist URL is required'}), 400

    if 'suno' not in playlist_url.lower():
        return jsonify({'error': 'URL must be a Suno playlist'}), 400

    # Download songs in background to avoid timeout
    # For now, we'll do it synchronously but this could be threaded
    result = download_suno_playlist(playlist_url, job.music_dir)

    # Track downloaded files in database
    for filename in result['downloaded']:
        filepath = job.music_dir / filename
        db.add_file(job_id, 'music', filename, str(filepath))

    return jsonify({
        'downloaded': result['downloaded'],
        'errors': result['errors'],
        'file_counts': job.get_file_counts()
    })


@app.route('/api/jobs/prepare', methods=['POST'])
def prepare_job():
    """Create a new job without starting it (for file uploads)"""
    with job_lock:
        # Get next job ID from database
        job_id = db.get_next_job_id()

        # Create run directory
        run_identifier = f"run-{job_id}-{uuid.uuid4().hex[:8]}"
        run_dir = RUNS_DIR / run_identifier

        # Create job with default config (will be updated later)
        default_config = {
            'duration': 600,
            'quotes_duration': 5.0,
            'quotes_min_between': 10.0,
            'quotes_max_between': 30.0,
            'fps': 30,
            'resolution': '1920x1080',
            'transition': 'crossfade',
            'music_volume': 0.7,
            'sounds_volume': 0.5,
            'quote_style': 'centered',
            'music_shuffle': False,
            'quotes_shuffle': False,
            'verbose': True
        }

        # Create job in database
        db.create_job(job_id, run_identifier, str(run_dir), default_config)

        # Create job object
        job = Job(job_id, default_config, run_dir, run_identifier)
        job.status = 'preparing'  # Special status for file upload phase
        jobs[job_id] = job

        # Update status in database
        db.update_job_status(job_id, 'preparing')

    return jsonify({
        'job_id': job_id,
        'run_id': run_identifier,
        'status': 'preparing'
    })


@app.route('/api/jobs/<int:job_id>/start', methods=['POST'])
def start_job(job_id):
    """Start a prepared job"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if job.status != 'preparing':
        return jsonify({'error': f'Job is already {job.status}'}), 400

    # Update config if provided
    if request.json:
        job.config.update(request.json)
        db.update_job_config(job_id, job.config)

    # Change status to queued
    job.update_status('queued')

    # Start job in background thread
    thread = threading.Thread(target=run_job, args=(job,), daemon=True)
    thread.start()

    return jsonify(job.to_dict())


@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Create and immediately start a video build job"""
    config = request.json

    with job_lock:
        # Get next job ID from database
        job_id = db.get_next_job_id()

        # Create run directory
        run_identifier = f"run-{job_id}-{uuid.uuid4().hex[:8]}"
        run_dir = RUNS_DIR / run_identifier

        # Create job in database
        db.create_job(job_id, run_identifier, str(run_dir), config)

        # Create job object
        job = Job(job_id, config, run_dir, run_identifier)
        jobs[job_id] = job

        # Start job in background thread
        thread = threading.Thread(target=run_job, args=(job,), daemon=True)
        thread.start()

    return jsonify({'job_id': job_id, 'run_id': run_identifier, 'status': 'queued'})


@app.route('/api/jobs/<int:job_id>')
def get_job(job_id):
    """Get job status"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(job.to_dict())


@app.route('/api/jobs/<int:job_id>/logs')
def get_job_logs(job_id):
    """Get job logs"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    logs = []
    while not job.log_queue.empty():
        try:
            logs.append(job.log_queue.get_nowait())
        except queue.Empty:
            break

    return jsonify({'logs': logs})


@app.route('/api/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a running job"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if job.process and job.status == 'running':
        job.process.terminate()
        job.update_status('cancelled')

    return jsonify(job.to_dict())


@app.route('/api/jobs')
def list_jobs():
    """List all jobs"""
    # Get jobs from database
    db_jobs = db.get_all_jobs()

    # Return jobs (mix of in-memory and database)
    all_jobs = []

    # First add in-memory jobs (current session)
    for job in jobs.values():
        all_jobs.append(job.to_dict())

    # Add database jobs that aren't in memory
    in_memory_ids = {job.job_id for job in jobs.values()}
    for db_job in db_jobs:
        if db_job['job_id'] not in in_memory_ids:
            # Create a minimal dict from database data
            all_jobs.append({
                'job_id': db_job['job_id'],
                'run_id': db_job['run_id'],
                'status': db_job['status'],
                'progress': db_job['progress'],
                'current_step': db_job['current_step'] or '',
                'output_file': db_job['output_file'],
                'error': db_job['error'],
                'file_counts': db.get_file_counts(db_job['job_id']),
                'created_at': db_job['created_at'],
                'started_at': db_job['started_at'],
                'finished_at': db_job['finished_at']
            })

    # Sort by created_at descending
    all_jobs.sort(key=lambda x: x['created_at'], reverse=True)

    return jsonify({'jobs': all_jobs})


@app.route('/api/jobs/<int:job_id>/download')
def download_job(job_id):
    """Download the output file"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if not job.output_file or not Path(job.output_file).exists():
        return jsonify({'error': 'Output file not found'}), 404

    return send_file(job.output_file, as_attachment=True)


# YouTube Upload Functionality
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# Store for YouTube credentials (in production, use a proper database)
youtube_credentials = {}


def get_youtube_service(user_id='default'):
    """Get authenticated YouTube service"""
    if not YOUTUBE_AVAILABLE:
        return None

    creds = youtube_credentials.get(user_id)
    if not creds:
        return None

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)


@app.route('/api/youtube/auth/status')
def youtube_auth_status():
    """Check if user is authenticated with YouTube"""
    if not YOUTUBE_AVAILABLE:
        return jsonify({'authenticated': False, 'error': 'YouTube API not available'})

    user_id = session.get('user_id', 'default')
    creds = youtube_credentials.get(user_id)

    return jsonify({
        'authenticated': creds is not None,
        'youtube_available': YOUTUBE_AVAILABLE
    })


@app.route('/api/youtube/auth/url')
def youtube_auth_url():
    """Get YouTube OAuth URL"""
    if not YOUTUBE_AVAILABLE:
        return jsonify({'error': 'YouTube API not available'}), 400

    # Check for client secrets file
    client_secrets_file = os.environ.get('YOUTUBE_CLIENT_SECRETS', 'secrets/client_secrets.json')

    if not os.path.exists(client_secrets_file):
        return jsonify({
            'error': 'YouTube OAuth not configured',
            'message': 'Please create secrets/client_secrets.json with your YouTube API credentials'
        }), 400

    try:
        flow = Flow.from_client_secrets_file(
            client_secrets_file,
            scopes=YOUTUBE_SCOPES,
            redirect_uri=url_for('youtube_auth_callback', _external=True)
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )

        session['oauth_state'] = state
        session['user_id'] = session.get('user_id', 'default')

        return jsonify({'auth_url': authorization_url})

    except Exception as e:
        return jsonify({'error': f'OAuth setup failed: {str(e)}'}), 500


@app.route('/api/youtube/auth/callback')
def youtube_auth_callback():
    """Handle YouTube OAuth callback"""
    if not YOUTUBE_AVAILABLE:
        return "YouTube API not available", 400

    state = session.get('oauth_state')
    client_secrets_file = os.environ.get('YOUTUBE_CLIENT_SECRETS', 'secrets/client_secrets.json')

    try:
        flow = Flow.from_client_secrets_file(
            client_secrets_file,
            scopes=YOUTUBE_SCOPES,
            state=state,
            redirect_uri=url_for('youtube_auth_callback', _external=True)
        )

        flow.fetch_token(authorization_response=request.url)

        credentials = flow.credentials
        user_id = session.get('user_id', 'default')
        youtube_credentials[user_id] = credentials

        return """
        <html>
            <body>
                <h2>YouTube Authentication Successful!</h2>
                <p>You can now close this window and return to the application.</p>
                <script>
                    window.close();
                </script>
            </body>
        </html>
        """

    except Exception as e:
        return f"Authentication failed: {str(e)}", 400


@app.route('/api/jobs/<int:job_id>/youtube/upload', methods=['POST'])
def upload_to_youtube(job_id):
    """Upload job output to YouTube"""
    if not YOUTUBE_AVAILABLE:
        return jsonify({'error': 'YouTube API not available'}), 400

    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if not job.output_file or not Path(job.output_file).exists():
        return jsonify({'error': 'Output file not found'}), 404

    user_id = session.get('user_id', 'default')
    youtube = get_youtube_service(user_id)

    if not youtube:
        return jsonify({'error': 'Not authenticated with YouTube'}), 401

    data = request.get_json()
    title = data.get('title', 'Video created with YT Builder')
    description = data.get('description', '')
    privacy = data.get('privacy', 'private')
    tags = data.get('tags', [])
    category = data.get('category', '22')  # Default to People & Blogs

    try:
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(
            job.output_file,
            chunksize=-1,
            resumable=True,
            mimetype='video/mp4'
        )

        request_obj = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request_obj.next_chunk()
            if status:
                print(f"[YouTube] Upload {int(status.progress() * 100)}% complete")

        video_id = response['id']
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Record upload in database
        db.add_youtube_upload(
            job_id=job_id,
            video_id=video_id,
            video_url=video_url,
            title=title,
            description=description,
            privacy=privacy,
            tags=tags,
            category=category
        )

        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_url': video_url,
            'message': f'Video uploaded successfully!'
        })

    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


def load_jobs_from_database():
    """Load existing jobs from database into memory"""
    print("Loading jobs from database...")

    db_jobs = db.get_all_jobs(limit=50)  # Load recent jobs

    for job_data in db_jobs:
        # Only load non-completed jobs into memory for potential resumption
        if job_data['status'] in ['preparing', 'queued']:
            try:
                job = Job.from_db(job_data)
                jobs[job.job_id] = job
                print(f"  Loaded job #{job.job_id} ({job.status})")
            except Exception as e:
                print(f"  Failed to load job #{job_data['job_id']}: {e}")

    print(f"Loaded {len(jobs)} active jobs from database")


if __name__ == '__main__':
    # Create output directory if it doesn't exist
    Path('output').mkdir(exist_ok=True)

    # Load existing jobs from database
    load_jobs_from_database()

    # Run the server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'

    print(f"")
    print(f"Starting YouTube Video Builder Web Server on http://localhost:{port}")
    print(f"Database: {db.db_path}")
    print(f"Press Ctrl+C to stop")
    print(f"")

    app.run(host='0.0.0.0', port=port, debug=debug)
