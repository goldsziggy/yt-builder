"""Configuration management for YouTube Video Builder"""

import os
from dataclasses import dataclass
from typing import Tuple
from pathlib import Path


@dataclass
class Config:
    """Configuration for video building process."""

    # Duration and timing
    duration: float
    quotes_duration: float
    quotes_min_between: float
    quotes_max_between: float

    # Shuffle options
    music_shuffle: bool
    quotes_shuffle: bool

    # Output options
    output_path: str
    fps: int
    resolution: Tuple[int, int]

    # Audio options
    music_volume: float
    sounds_volume: float

    # Visual options
    quote_style: str
    transition: str

    # Utility options
    verbose: bool
    dry_run: bool

    # Directory paths (can be overridden)
    videos_dir: Path = Path('videos')
    music_dir: Path = Path('music')
    quotes_dir: Path = Path('quotes')
    sounds_dir: Path = Path('sounds')
    temp_dir: Path = Path('.tmp')

    def __post_init__(self):
        """Initialize derived properties."""
        # Override directories from environment variables if set
        if 'YT_BUILDER_VIDEOS_DIR' in os.environ:
            self.videos_dir = Path(os.environ['YT_BUILDER_VIDEOS_DIR'])
        if 'YT_BUILDER_MUSIC_DIR' in os.environ:
            self.music_dir = Path(os.environ['YT_BUILDER_MUSIC_DIR'])
        if 'YT_BUILDER_QUOTES_DIR' in os.environ:
            self.quotes_dir = Path(os.environ['YT_BUILDER_QUOTES_DIR'])
        if 'YT_BUILDER_SOUNDS_DIR' in os.environ:
            self.sounds_dir = Path(os.environ['YT_BUILDER_SOUNDS_DIR'])
        if 'YT_BUILDER_TEMP_DIR' in os.environ:
            self.temp_dir = Path(os.environ['YT_BUILDER_TEMP_DIR'])

        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Convert output path to Path object
        if isinstance(self.output_path, str):
            self.output_path = Path(self.output_path)
