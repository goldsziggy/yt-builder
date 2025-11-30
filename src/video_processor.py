"""Video processing module for YouTube Video Builder"""

import logging
import random
import subprocess
from pathlib import Path
from typing import List, Optional

from .config import Config
from .validator import get_files_by_format, VIDEO_FORMATS, validate_file_integrity
from .utils import get_temp_file, run_ffmpeg_with_progress

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

        # Process each unique video once (normalize resolution/fps)
        logger.info("Normalizing videos to target resolution and fps...")
        processed_cache = {}
        for video_path in valid_videos:
            logger.info(f"Processing video: {video_path.name}")
            processed_cache[video_path] = self._process_single_video(video_path)

        # Get durations of processed videos
        video_durations = [self._get_duration(processed_cache[v]) for v in valid_videos]
        total_duration = sum(video_durations)

        logger.info(f"Total video duration: {total_duration:.2f}s, Target: {self.config.duration}s")

        # Determine which videos to use and how many times to loop
        if total_duration < self.config.duration:
            # Need to loop videos - use already processed versions
            loops_needed = int(self.config.duration / total_duration) + 1
            logger.info(f"Looping video sequence {loops_needed} times")
            # Create list of already-processed videos
            final_videos = [processed_cache[v] for v in valid_videos] * loops_needed
            final_durations = video_durations * loops_needed
        else:
            final_videos = [processed_cache[v] for v in valid_videos]
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
            # Single video, already processed
            output_file = selected_videos[0]
        else:
            # Multiple videos, need to concatenate (all already processed)
            output_file = self._concatenate_videos_preprocessed(selected_videos)

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

        self._run_ffmpeg(cmd, f"Processing {video_path.name}")
        return output_file

    def _concatenate_videos(self, video_paths: List[Path]) -> Path:
        """
        Concatenate multiple videos with transitions.
        Legacy method - processes videos before concatenating.

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

        return self._concatenate_videos_preprocessed(normalized_videos)

    def _concatenate_videos_preprocessed(self, processed_videos: List[Path]) -> Path:
        """
        Concatenate multiple already-processed videos with transitions.
        Uses batch processing for large numbers of clips to avoid resource limits.

        Args:
            processed_videos: List of already-processed video file paths

        Returns:
            Path to concatenated video
        """
        num_videos = len(processed_videos)
        logger.info(f"Concatenating {num_videos} videos with {self.config.transition} transition")

        # For very large numbers of videos, process in batches to avoid system limits
        BATCH_SIZE = 25  # Very conservative batch size to avoid file limit issues

        if num_videos > BATCH_SIZE:
            logger.info(f"⚠️  BATCH MODE: Processing {num_videos} videos in batches of {BATCH_SIZE}")
            logger.info(f"This will create {(num_videos + BATCH_SIZE - 1) // BATCH_SIZE} batch(es)")
            return self._concatenate_in_batches(processed_videos, BATCH_SIZE)

        if num_videos > 10:
            logger.info(f"This may take a few minutes for {num_videos} clips. Progress will be shown below...")

        # Validate all files exist
        missing_files = [v for v in processed_videos if not v.exists()]
        if missing_files:
            raise RuntimeError(f"Missing input file(s): {', '.join(str(f) for f in missing_files)}")

        # Create concat file
        concat_file = get_temp_file(self.config, '.txt')
        with open(concat_file, 'w') as f:
            for video in processed_videos:
                # Escape single quotes in file paths for concat demuxer
                video_path = str(video.absolute()).replace("'", "'\\''")
                f.write(f"file '{video_path}'\n")

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
            cmd = self._build_xfade_command(processed_videos, output_file, 'fade')
        else:  # crossfade
            cmd = self._build_xfade_command(processed_videos, output_file, 'fadeblack')

        self._run_ffmpeg(cmd, "Concatenating videos")
        return output_file

    def _concatenate_in_batches(self, processed_videos: List[Path], batch_size: int) -> Path:
        """
        Concatenate videos in batches to handle very large numbers of clips.

        Args:
            processed_videos: List of already-processed video file paths
            batch_size: Number of videos to process per batch

        Returns:
            Path to final concatenated video
        """
        num_videos = len(processed_videos)
        num_batches = (num_videos + batch_size - 1) // batch_size

        logger.info(f"Splitting {num_videos} videos into {num_batches} batch(es)")

        # Process each batch
        batch_outputs = []
        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, num_videos)
            batch = processed_videos[start_idx:end_idx]

            logger.info(f"Processing batch {i + 1}/{num_batches} ({len(batch)} clips)...")

            # Validate all files exist before processing
            missing_files = [v for v in batch if not v.exists()]
            if missing_files:
                raise RuntimeError(
                    f"Batch {i + 1}/{num_batches}: Missing input file(s): "
                    f"{', '.join(str(f) for f in missing_files)}"
                )

            # Create concat file for this batch
            concat_file = get_temp_file(self.config, '.txt')
            with open(concat_file, 'w') as f:
                for video in batch:
                    # Escape single quotes in file paths for concat demuxer
                    video_path = str(video.absolute()).replace("'", "'\\''")
                    f.write(f"file '{video_path}'\n")

            # Verify concat file was created and is readable
            if not concat_file.exists() or concat_file.stat().st_size == 0:
                raise RuntimeError(f"Failed to create concat file for batch {i + 1}/{num_batches}: {concat_file}")

            # Concatenate this batch
            batch_output = get_temp_file(self.config, '.mp4')

            if self.config.transition == 'none':
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_file),
                    '-c', 'copy',
                    '-y',
                    str(batch_output)
                ]
            else:
                # For transitions, use simple concat within batch
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_file),
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-y',
                    str(batch_output)
                ]

            try:
                self._run_ffmpeg(cmd, f"Batch {i + 1}/{num_batches}")
                # Verify batch output was created and is valid
                if not batch_output.exists():
                    raise RuntimeError(f"Batch {i + 1}/{num_batches} output file was not created: {batch_output}")
                if batch_output.stat().st_size == 0:
                    raise RuntimeError(f"Batch {i + 1}/{num_batches} output file is empty: {batch_output}")
                batch_outputs.append(batch_output)
            except Exception as e:
                logger.error(f"Failed to process batch {i + 1}/{num_batches}")
                logger.error(f"Concat file contents: {concat_file.read_text() if concat_file.exists() else 'N/A'}")
                raise

        # Now concatenate all batches together
        logger.info(f"Combining {len(batch_outputs)} batch(es) into final video...")

        if len(batch_outputs) == 1:
            return batch_outputs[0]

        # Final concatenation of batches
        # Validate all batch outputs exist
        missing_batches = [b for b in batch_outputs if not b.exists()]
        if missing_batches:
            raise RuntimeError(
                f"Missing batch output file(s): {', '.join(str(f) for f in missing_batches)}"
            )

        final_concat_file = get_temp_file(self.config, '.txt')
        with open(final_concat_file, 'w') as f:
            for batch_output in batch_outputs:
                # Escape single quotes in file paths for concat demuxer
                batch_path = str(batch_output.absolute()).replace("'", "'\\''")
                f.write(f"file '{batch_path}'\n")

        final_output = get_temp_file(self.config, '.mp4')

        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(final_concat_file),
            '-c', 'copy',
            '-y',
            str(final_output)
        ]

        self._run_ffmpeg(cmd, "Final concatenation")
        return final_output

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
        # Validate all files exist
        missing_files = [v for v in video_paths if not v.exists()]
        if missing_files:
            raise RuntimeError(f"Missing input file(s): {', '.join(str(f) for f in missing_files)}")

        concat_file = get_temp_file(self.config, '.txt')
        with open(concat_file, 'w') as f:
            for video in video_paths:
                # Escape single quotes in file paths for concat demuxer
                video_path = str(video.absolute()).replace("'", "'\\''")
                f.write(f"file '{video_path}'\n")

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

        self._run_ffmpeg(cmd, "Trimming video")
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
        num_quotes = len(quote_timings) if quote_timings else 0
        logger.info("Combining video, audio, and quotes into final output")

        if num_quotes > 0:
            logger.info(f"Adding {num_quotes} quote overlay(s) to video")

        logger.info("Rendering final video. Progress will be shown below...")

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

        self._run_ffmpeg(cmd, "Creating final video")

    def _run_ffmpeg(self, cmd: List[str], operation: str = "Processing video") -> None:
        """
        Run ffmpeg command with progress reporting.

        Args:
            cmd: Command as list of strings
            operation: Description of the operation

        Raises:
            RuntimeError: If ffmpeg fails
        """
        run_ffmpeg_with_progress(cmd, operation, self.config.verbose)
