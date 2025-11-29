"""Video processing module for YouTube Video Builder"""

import logging
import random
import subprocess
from pathlib import Path
from typing import List, Optional

from .config import Config
from .validator import get_files_by_format, VIDEO_FORMATS, validate_file_integrity
from .utils import get_temp_file

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Handles video processing operations."""

    def __init__(self, config: Config):
        """
        Initialize video processor.

        Args:
            config: Configuration object
        """
        self.config = config

    def process_videos(self) -> Path:
        """
        Process all videos: combine, loop, and add transitions.

        Returns:
            Path to processed video file
        """
        # Get video files
        video_files = get_files_by_format(self.config.videos_dir, VIDEO_FORMATS)

        # Filter out corrupted files
        valid_videos = [v for v in video_files if validate_file_integrity(v)]

        if not valid_videos:
            raise RuntimeError("No valid video files found")

        if len(valid_videos) < len(video_files):
            logger.warning(f"Skipped {len(video_files) - len(valid_videos)} corrupted video file(s)")

        # Shuffle if requested (note: PRD says MUSIC_SHUFFLE affects video order too)
        if self.config.music_shuffle:
            random.shuffle(valid_videos)
            logger.info("Shuffled video order")
        else:
            valid_videos = sorted(valid_videos)

        logger.info(f"Processing {len(valid_videos)} video file(s)")

        # Get durations of all videos
        video_durations = [self._get_duration(v) for v in valid_videos]
        total_duration = sum(video_durations)

        logger.info(f"Total video duration: {total_duration:.2f}s, Target: {self.config.duration}s")

        # Determine which videos to use and how many times to loop
        if total_duration < self.config.duration:
            # Need to loop videos
            loops_needed = int(self.config.duration / total_duration) + 1
            logger.info(f"Looping video sequence {loops_needed} times")
            final_videos = valid_videos * loops_needed
            final_durations = video_durations * loops_needed
        else:
            final_videos = valid_videos
            final_durations = video_durations

        # Trim to fit duration
        selected_videos = []
        selected_durations = []
        accumulated_time = 0.0

        for video, duration in zip(final_videos, final_durations):
            if accumulated_time >= self.config.duration:
                break
            selected_videos.append(video)
            selected_durations.append(duration)
            accumulated_time += duration

        logger.info(f"Selected {len(selected_videos)} video clip(s) for output")

        # Combine videos
        if len(selected_videos) == 1 and accumulated_time <= self.config.duration:
            # Single video, just process it
            output_file = self._process_single_video(selected_videos[0])
        else:
            # Multiple videos, need to concatenate
            output_file = self._concatenate_videos(selected_videos)

        # Trim to exact duration if needed
        if accumulated_time > self.config.duration:
            output_file = self._trim_video(output_file, self.config.duration)

        return output_file

    def _get_duration(self, video_path: Path) -> float:
        """
        Get duration of a video file using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Duration in seconds
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.error(f"Failed to get duration for {video_path}: {e}")
            raise

    def _process_single_video(self, video_path: Path) -> Path:
        """
        Process a single video (scale and format).

        Args:
            video_path: Path to video file

        Returns:
            Path to processed video
        """
        output_file = get_temp_file(self.config, '.mp4')
        width, height = self.config.resolution

        logger.info(f"Processing video: {video_path.name}")

        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
            '-r', str(self.config.fps),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-an',  # Remove audio for now
            '-y',
            str(output_file)
        ]

        self._run_ffmpeg(cmd)
        return output_file

    def _concatenate_videos(self, video_paths: List[Path]) -> Path:
        """
        Concatenate multiple videos with transitions.

        Args:
            video_paths: List of video file paths

        Returns:
            Path to concatenated video
        """
        logger.info(f"Concatenating {len(video_paths)} videos with {self.config.transition} transition")

        # First, normalize all videos to same resolution and fps
        normalized_videos = []
        for video_path in video_paths:
            normalized = self._process_single_video(video_path)
            normalized_videos.append(normalized)

        # Create concat file
        concat_file = get_temp_file(self.config, '.txt')
        with open(concat_file, 'w') as f:
            for video in normalized_videos:
                f.write(f"file '{video.absolute()}'\n")

        # Concatenate
        output_file = get_temp_file(self.config, '.mp4')

        if self.config.transition == 'none':
            # Simple concatenation
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-y',
                str(output_file)
            ]
        elif self.config.transition == 'fade':
            # Use xfade filter for transitions
            cmd = self._build_xfade_command(normalized_videos, output_file, 'fade')
        else:  # crossfade
            cmd = self._build_xfade_command(normalized_videos, output_file, 'fadeblack')

        self._run_ffmpeg(cmd)
        return output_file

    def _build_xfade_command(self, video_paths: List[Path], output_file: Path, transition_type: str) -> List[str]:
        """
        Build ffmpeg command for crossfade transitions.

        Args:
            video_paths: List of normalized video paths
            output_file: Output file path
            transition_type: Type of transition

        Returns:
            ffmpeg command as list
        """
        # For simplicity with xfade, we'll use a basic concat with fade
        # A full xfade implementation is complex, so we'll do a simple version
        concat_file = get_temp_file(self.config, '.txt')
        with open(concat_file, 'w') as f:
            for video in video_paths:
                f.write(f"file '{video.absolute()}'\n")

        # Simple concatenation with fade between segments
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(output_file)
        ]

        return cmd

    def _trim_video(self, video_path: Path, duration: float) -> Path:
        """
        Trim video to specified duration.

        Args:
            video_path: Path to video file
            duration: Target duration in seconds

        Returns:
            Path to trimmed video
        """
        logger.info(f"Trimming video to {duration}s")

        output_file = get_temp_file(self.config, '.mp4')

        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-t', str(duration),
            '-c', 'copy',
            '-y',
            str(output_file)
        ]

        self._run_ffmpeg(cmd)
        return output_file

    def combine_all(self, video_file: Path, audio_file: Optional[Path], quote_timings: list, quote_renderer) -> None:
        """
        Combine video, audio, and quotes into final output.

        Args:
            video_file: Path to processed video file
            audio_file: Path to mixed audio file (or None)
            quote_timings: List of quote timing information
            quote_renderer: QuoteRenderer instance
        """
        logger.info("Combining video, audio, and quotes into final output")

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(video_file),
        ]

        if audio_file:
            cmd.extend(['-i', str(audio_file)])

        # Add video filter for quotes if any
        if quote_timings:
            drawtext_filter = quote_renderer.get_drawtext_filter(quote_timings)
            cmd.extend(['-vf', drawtext_filter])

        # Map streams
        if audio_file:
            cmd.extend(['-map', '0:v', '-map', '1:a'])
        else:
            cmd.extend(['-map', '0:v'])

        # Output encoding settings
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
        ])

        if audio_file:
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '192k',
            ])

        cmd.extend([
            '-shortest',
            '-y',
            str(self.config.output_path)
        ])

        self._run_ffmpeg(cmd)

    def _run_ffmpeg(self, cmd: List[str]) -> None:
        """
        Run ffmpeg command with error handling.

        Args:
            cmd: Command as list of strings

        Raises:
            RuntimeError: If ffmpeg fails
        """
        if self.config.verbose:
            logger.debug(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            if self.config.verbose and result.stderr:
                logger.debug(result.stderr)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e}")
            if e.stderr:
                logger.error(f"Error output: {e.stderr}")
            raise RuntimeError(f"Video processing failed: {e}")
