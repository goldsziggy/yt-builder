"""Input validation for YouTube Video Builder"""

import logging
from pathlib import Path
from typing import List

from .config import Config

logger = logging.getLogger(__name__)

# Supported file formats
VIDEO_FORMATS = {'.mp4', '.mov', '.avi', '.mkv'}
AUDIO_FORMATS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg'}
QUOTE_FORMATS = {'.txt'}


def validate_inputs(config: Config) -> None:
    """
    Validate all inputs before processing.

    Args:
        config: Configuration object

    Raises:
        ValueError: If validation fails
    """
    # Validate duration
    if config.duration <= 0:
        raise ValueError(f"Duration must be positive, got: {config.duration}")

    # Validate quote timing
    if config.quotes_duration <= 0:
        raise ValueError(f"Quote duration must be positive, got: {config.quotes_duration}")

    if config.quotes_min_between < 0:
        raise ValueError(f"Quotes min between must be non-negative, got: {config.quotes_min_between}")

    if config.quotes_max_between < config.quotes_min_between:
        raise ValueError(
            f"Quotes max between ({config.quotes_max_between}) must be >= "
            f"quotes min between ({config.quotes_min_between})"
        )

    # Validate volume levels
    if not 0.0 <= config.music_volume <= 1.0:
        raise ValueError(f"Music volume must be between 0.0 and 1.0, got: {config.music_volume}")

    if not 0.0 <= config.sounds_volume <= 1.0:
        raise ValueError(f"Sounds volume must be between 0.0 and 1.0, got: {config.sounds_volume}")

    # Validate FPS
    if config.fps <= 0:
        raise ValueError(f"FPS must be positive, got: {config.fps}")

    # Validate resolution
    width, height = config.resolution
    if width <= 0 or height <= 0:
        raise ValueError(f"Resolution must have positive dimensions, got: {width}x{height}")

    # Validate directories
    validate_directory_structure(config)


def validate_directory_structure(config: Config) -> None:
    """
    Validate directory structure and file availability.

    Args:
        config: Configuration object

    Raises:
        ValueError: If required directories/files are missing
    """
    # Check videos directory
    if not config.videos_dir.exists():
        raise ValueError(f"Videos directory does not exist: {config.videos_dir}")

    video_files = get_files_by_format(config.videos_dir, VIDEO_FORMATS)
    if not video_files:
        raise ValueError(f"No video files found in {config.videos_dir}. Required formats: {VIDEO_FORMATS}")

    logger.info(f"Found {len(video_files)} video file(s)")

    # Check music directory (optional but warn if empty)
    if not config.music_dir.exists():
        logger.warning(f"Music directory does not exist: {config.music_dir}")
        logger.warning("Video will be created without background music")
    else:
        music_files = get_files_by_format(config.music_dir, AUDIO_FORMATS)
        if not music_files:
            logger.warning(f"No music files found in {config.music_dir}")
            logger.warning("Video will be created without background music")
        else:
            logger.info(f"Found {len(music_files)} music file(s)")

    # Check quotes directory (optional but warn if empty)
    if not config.quotes_dir.exists():
        logger.warning(f"Quotes directory does not exist: {config.quotes_dir}")
        logger.warning("Video will be created without quotes")
    else:
        quote_files = get_files_by_format(config.quotes_dir, QUOTE_FORMATS)
        if not quote_files:
            logger.warning(f"No quote files found in {config.quotes_dir}")
            logger.warning("Video will be created without quotes")
        else:
            logger.info(f"Found {len(quote_files)} quote file(s)")

    # Check sounds directory (optional, no warning if empty)
    if config.sounds_dir.exists():
        sound_files = get_files_by_format(config.sounds_dir, AUDIO_FORMATS)
        if sound_files:
            logger.info(f"Found {len(sound_files)} sound file(s)")
    else:
        logger.debug(f"Sounds directory does not exist: {config.sounds_dir}")


def get_files_by_format(directory: Path, formats: set) -> List[Path]:
    """
    Get all files in directory matching the given formats.

    Args:
        directory: Directory to search
        formats: Set of file extensions (including dot)

    Returns:
        List of matching file paths
    """
    if not directory.exists():
        return []

    files = []
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in formats:
            files.append(file_path)

    return sorted(files)


def validate_file_integrity(file_path: Path) -> bool:
    """
    Check if a media file is valid and not corrupted.

    Args:
        file_path: Path to media file

    Returns:
        True if file is valid, False otherwise
    """
    # Basic check: file exists and has non-zero size
    if not file_path.exists():
        logger.error(f"File does not exist: {file_path}")
        return False

    if file_path.stat().st_size == 0:
        logger.error(f"File is empty: {file_path}")
        return False

    # Could add more sophisticated checks with ffprobe here
    return True
