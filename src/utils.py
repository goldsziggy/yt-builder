"""Utility functions for YouTube Video Builder"""

import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, List

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


def _format_eta(seconds: float) -> str:
    """
    Format ETA in a human-readable format.

    Args:
        seconds: Remaining seconds

    Returns:
        Formatted ETA string
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


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


def run_ffmpeg_with_progress(cmd: List[str], operation: str = "Processing", verbose: bool = False) -> None:
    """
    Run ffmpeg command with real-time progress reporting.

    Args:
        cmd: Command as list of strings
        operation: Description of the operation
        verbose: Show detailed ffmpeg output

    Raises:
        RuntimeError: If ffmpeg fails
    """
    logger = logging.getLogger(__name__)

    if verbose:
        logger.debug(f"Running: {' '.join(cmd)}")

    # Add -stats flag to force progress output even when piped
    cmd_with_stats = cmd.copy()
    # Insert after 'ffmpeg' command
    if '-stats' not in cmd_with_stats:
        cmd_with_stats.insert(1, '-stats')

    try:
        # Run ffmpeg with stats output to stderr
        process = subprocess.Popen(
            cmd_with_stats,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout
            text=True,
            bufsize=0  # Unbuffered
        )

        duration_pattern = re.compile(r'Duration:\s*(\d{2}):(\d{2}):(\d{2}\.\d{2})')
        time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})')
        speed_pattern = re.compile(r'speed=\s*(\d+\.?\d*)x')

        total_duration = None
        last_progress = -1
        all_output = []

        # Read output line by line
        for line in iter(process.stdout.readline, ''):
            if not line:
                break

            all_output.append(line)

            # Extract total duration
            if total_duration is None:
                duration_match = duration_pattern.search(line)
                if duration_match:
                    h, m, s = duration_match.groups()
                    total_duration = int(h) * 3600 + int(m) * 60 + float(s)
                    if verbose:
                        logger.debug(f"Detected duration: {total_duration:.2f}s")

            # Extract current time and show progress
            time_match = time_pattern.search(line)
            if time_match and total_duration:
                h, m, s = time_match.groups()
                current_time = int(h) * 3600 + int(m) * 60 + float(s)

                progress = int((current_time / total_duration) * 100)

                # Only update if progress changed
                if progress != last_progress and progress <= 100:
                    # Extract speed if available
                    speed_match = speed_pattern.search(line)
                    speed = float(speed_match.group(1)) if speed_match else None

                    # Calculate ETA
                    eta_str = ""
                    if speed and speed > 0:
                        remaining_video_time = total_duration - current_time
                        remaining_real_time = remaining_video_time / speed
                        eta_str = f" ETA: {_format_eta(remaining_real_time)}"

                    speed_str = f" ({speed}x)" if speed else ""

                    # Print progress on same line
                    print(f"\r{operation}: {progress}% [{current_time:.1f}/{total_duration:.1f}s]{speed_str}{eta_str}",
                          end='', file=sys.stderr, flush=True)
                    last_progress = progress

        # Wait for process to complete
        return_code = process.wait()

        # Print newline after progress
        if last_progress >= 0:
            print(file=sys.stderr)

        if return_code != 0:
            error_output = ''.join(all_output)
            # Always show last 50 lines of output on error
            error_lines = error_output.split('\n')
            recent_output = '\n'.join(error_lines[-50:])
            logger.error(f"FFmpeg failed with exit code {return_code}")
            logger.error(f"Command: {' '.join(cmd)}")
            if error_output.strip():
                logger.error(f"Last 50 lines of output:\n{recent_output}")
            else:
                logger.error("No error output captured from FFmpeg")
            raise subprocess.CalledProcessError(return_code, cmd, output=error_output)

        if verbose:
            logger.debug(''.join(all_output))

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e}")
        raise RuntimeError(f"FFmpeg operation failed: {operation}")
    except Exception as e:
        logger.error(f"Unexpected error running ffmpeg: {e}")
        raise RuntimeError(f"FFmpeg operation failed: {operation}")
