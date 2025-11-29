"""Utility functions for YouTube Video Builder"""

import logging
import shutil
from pathlib import Path
from typing import Optional

from .config import Config


def setup_logging(level: int = logging.INFO) -> None:
    """
    Setup logging configuration.

    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def check_disk_space(directory: Path, required_bytes: int) -> None:
    """
    Check if sufficient disk space is available.

    Args:
        directory: Directory to check
        required_bytes: Required space in bytes

    Raises:
        RuntimeError: If insufficient disk space
    """
    stat = shutil.disk_usage(directory)
    available_bytes = stat.free

    # Add 10% buffer
    required_with_buffer = required_bytes * 1.1

    if available_bytes < required_with_buffer:
        available_gb = available_bytes / (1024 ** 3)
        required_gb = required_with_buffer / (1024 ** 3)
        raise RuntimeError(
            f"Insufficient disk space. Available: {available_gb:.2f} GB, "
            f"Required: {required_gb:.2f} GB"
        )


def estimate_output_size(config: Config) -> int:
    """
    Estimate output file size in bytes.

    Args:
        config: Configuration object

    Returns:
        Estimated size in bytes
    """
    # Rough estimation: bitrate * duration
    # Assuming H.264 at ~5 Mbps for 1080p
    width, height = config.resolution
    pixels = width * height

    # Estimate bitrate based on resolution
    if pixels >= 1920 * 1080:  # 1080p or higher
        bitrate_mbps = 5.0
    elif pixels >= 1280 * 720:  # 720p
        bitrate_mbps = 2.5
    else:  # Lower resolutions
        bitrate_mbps = 1.5

    # Convert to bytes per second
    bitrate_bps = bitrate_mbps * 1_000_000 / 8

    # Estimate size
    estimated_bytes = int(bitrate_bps * config.duration)

    return estimated_bytes


def format_time(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def cleanup_temp_files(config: Config) -> None:
    """
    Clean up temporary files.

    Args:
        config: Configuration object
    """
    logger = logging.getLogger(__name__)

    if config.temp_dir.exists():
        try:
            shutil.rmtree(config.temp_dir)
            logger.debug(f"Cleaned up temporary directory: {config.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory: {e}")


def get_temp_file(config: Config, suffix: str = '.mp4') -> Path:
    """
    Generate a unique temporary file path.

    Args:
        config: Configuration object
        suffix: File suffix

    Returns:
        Path to temporary file
    """
    import uuid
    config.temp_dir.mkdir(exist_ok=True)
    return config.temp_dir / f"temp_{uuid.uuid4().hex}{suffix}"
