"""Database module for YouTube Video Builder"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager


class Database:
    """SQLite database for tracking jobs and uploads"""

    def __init__(self, db_path: str = 'data/yt-builder.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Jobs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id INTEGER PRIMARY KEY,
                    run_id TEXT NOT NULL UNIQUE,
                    run_dir TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER DEFAULT 0,
                    current_step TEXT,
                    config TEXT,
                    output_file TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                )
            ''')

            # File tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    file_type TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE,
                    UNIQUE (job_id, file_type, filename)
                )
            ''')

            # YouTube uploads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS youtube_uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    video_id TEXT NOT NULL,
                    video_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    privacy TEXT NOT NULL,
                    tags TEXT,
                    category TEXT,
                    uploaded_at TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE
                )
            ''')

            # YouTube credentials table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS youtube_credentials (
                    user_id TEXT PRIMARY KEY,
                    credentials_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_files_job ON job_files(job_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_youtube_job ON youtube_uploads(job_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_youtube_creds_user ON youtube_credentials(user_id)')

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_job(self, job_id: int, run_id: str, run_dir: str, config: Dict) -> bool:
        """Create a new job"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO jobs (job_id, run_id, run_dir, status, config, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                job_id,
                run_id,
                run_dir,
                'preparing',
                json.dumps(config),
                datetime.now().isoformat()
            ))
            conn.commit()
            return True

    def get_job(self, job_id: int) -> Optional[Dict]:
        """Get job by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

    def get_all_jobs(self, limit: int = 100) -> List[Dict]:
        """Get all jobs, newest first"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM jobs
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def update_job_status(self, job_id: int, status: str, **kwargs) -> bool:
        """Update job status and optional fields"""
        fields = ['status = ?']
        values = [status]

        # Handle optional fields
        if 'progress' in kwargs:
            fields.append('progress = ?')
            values.append(kwargs['progress'])

        if 'current_step' in kwargs:
            fields.append('current_step = ?')
            values.append(kwargs['current_step'])

        if 'output_file' in kwargs:
            fields.append('output_file = ?')
            values.append(kwargs['output_file'])

        if 'error' in kwargs:
            fields.append('error = ?')
            values.append(kwargs['error'])

        if status == 'running' and 'started_at' not in kwargs:
            fields.append('started_at = ?')
            values.append(datetime.now().isoformat())

        if status in ['completed', 'failed', 'cancelled']:
            fields.append('finished_at = ?')
            values.append(datetime.now().isoformat())

        values.append(job_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE jobs
                SET {', '.join(fields)}
                WHERE job_id = ?
            ''', values)
            conn.commit()
            return cursor.rowcount > 0

    def update_job_config(self, job_id: int, config: Dict) -> bool:
        """Update job configuration"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE jobs
                SET config = ?
                WHERE job_id = ?
            ''', (json.dumps(config), job_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_file(self, job_id: int, file_type: str, filename: str, file_path: str) -> bool:
        """Add a file to job tracking"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO job_files (job_id, file_type, filename, file_path, uploaded_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    job_id,
                    file_type,
                    filename,
                    file_path,
                    datetime.now().isoformat()
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # File already exists, update it
                cursor.execute('''
                    UPDATE job_files
                    SET file_path = ?, uploaded_at = ?
                    WHERE job_id = ? AND file_type = ? AND filename = ?
                ''', (
                    file_path,
                    datetime.now().isoformat(),
                    job_id,
                    file_type,
                    filename
                ))
                conn.commit()
                return True

    def get_job_files(self, job_id: int, file_type: Optional[str] = None) -> List[Dict]:
        """Get files for a job"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if file_type:
                cursor.execute('''
                    SELECT * FROM job_files
                    WHERE job_id = ? AND file_type = ?
                    ORDER BY uploaded_at DESC
                ''', (job_id, file_type))
            else:
                cursor.execute('''
                    SELECT * FROM job_files
                    WHERE job_id = ?
                    ORDER BY file_type, filename
                ''', (job_id,))

            return [dict(row) for row in cursor.fetchall()]

    def delete_file(self, job_id: int, file_type: str, filename: str) -> bool:
        """Delete a file from tracking"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM job_files
                WHERE job_id = ? AND file_type = ? AND filename = ?
            ''', (job_id, file_type, filename))
            conn.commit()
            return cursor.rowcount > 0

    def get_file_counts(self, job_id: int) -> Dict[str, int]:
        """Get count of files by type for a job"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT file_type, COUNT(*) as count
                FROM job_files
                WHERE job_id = ?
                GROUP BY file_type
            ''', (job_id,))

            counts = {
                'videos': 0,
                'music': 0,
                'sounds': 0,
                'quotes': 0
            }

            for row in cursor.fetchall():
                counts[row['file_type']] = row['count']

            return counts

    def add_youtube_upload(self, job_id: int, video_id: str, video_url: str,
                          title: str, description: str, privacy: str,
                          tags: List[str], category: str) -> bool:
        """Record a YouTube upload"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO youtube_uploads
                (job_id, video_id, video_url, title, description, privacy, tags, category, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id,
                video_id,
                video_url,
                title,
                description,
                privacy,
                json.dumps(tags),
                category,
                datetime.now().isoformat()
            ))
            conn.commit()
            return True

    def get_youtube_uploads(self, job_id: Optional[int] = None) -> List[Dict]:
        """Get YouTube uploads"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if job_id:
                cursor.execute('''
                    SELECT * FROM youtube_uploads
                    WHERE job_id = ?
                    ORDER BY uploaded_at DESC
                ''', (job_id,))
            else:
                cursor.execute('''
                    SELECT * FROM youtube_uploads
                    ORDER BY uploaded_at DESC
                    LIMIT 100
                ''')

            results = []
            for row in cursor.fetchall():
                data = dict(row)
                data['tags'] = json.loads(data['tags'])
                results.append(data)

            return results

    def get_next_job_id(self) -> int:
        """Get the next available job ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(job_id) as max_id FROM jobs')
            row = cursor.fetchone()
            max_id = row['max_id'] if row['max_id'] is not None else 0
            return max_id + 1

    def get_old_preparing_jobs(self, hours: int = 1) -> List[Dict]:
        """Get preparing jobs older than specified hours"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = datetime.now().timestamp() - (hours * 60 * 60)
            cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

            cursor.execute('''
                SELECT * FROM jobs
                WHERE status = 'preparing' AND created_at < ?
                ORDER BY created_at ASC
            ''', (cutoff_iso,))

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def delete_job(self, job_id: int) -> bool:
        """Delete a job and its associated data (CASCADE will handle related records)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM jobs WHERE job_id = ?', (job_id,))
            conn.commit()
            return cursor.rowcount > 0

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """Delete jobs older than specified days"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

            cursor.execute('''
                DELETE FROM jobs
                WHERE finished_at < ? AND finished_at IS NOT NULL
            ''', (cutoff_iso,))

            conn.commit()
            return cursor.rowcount

    def save_youtube_credentials(self, user_id: str, credentials_json: str) -> bool:
        """Save YouTube OAuth credentials for a user"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO youtube_credentials (user_id, credentials_json, updated_at)
                VALUES (?, ?, ?)
            ''', (
                user_id,
                credentials_json,
                datetime.now().isoformat()
            ))
            conn.commit()
            return True

    def get_youtube_credentials(self, user_id: str) -> Optional[str]:
        """Get YouTube OAuth credentials for a user"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT credentials_json FROM youtube_credentials
                WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            if row:
                return row['credentials_json']
            return None

    def delete_youtube_credentials(self, user_id: str) -> bool:
        """Delete YouTube OAuth credentials for a user"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM youtube_credentials WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert database row to dictionary"""
        data = dict(row)

        # Parse JSON fields
        if 'config' in data and data['config']:
            data['config'] = json.loads(data['config'])

        return data
