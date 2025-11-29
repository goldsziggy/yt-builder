"""Configuration management for YouTube Video Builder"""

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
        # Ensure temp directory exists
        self.temp_dir.mkdir(exist_ok=True)

        # Convert output path to Path object
        if isinstance(self.output_path, str):
            self.output_path = Path(self.output_path)
