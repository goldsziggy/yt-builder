"""Audio mixing module for YouTube Video Builder"""

import logging
import random
import subprocess
from pathlib import Path
from typing import List, Optional

from .config import Config
from .validator import get_files_by_format, AUDIO_FORMATS, validate_file_integrity
from .utils import get_temp_file

logger = logging.getLogger(__name__)


class AudioMixer:
    """Handles audio mixing operations."""

    def __init__(self, config: Config):
        """
        Initialize audio mixer.

        Args:
            config: Configuration object
        """
        self.config = config

    def mix_audio(self) -> Optional[Path]:
        """
        Mix all audio tracks (music + sounds).

        Returns:
            Path to mixed audio file, or None if no audio files
        """
        # Get music and sound files
        music_files = get_files_by_format(self.config.music_dir, AUDIO_FORMATS)
        sound_files = get_files_by_format(self.config.sounds_dir, AUDIO_FORMATS)

        # Filter valid files
        valid_music = [f for f in music_files if validate_file_integrity(f)]
        valid_sounds = [f for f in sound_files if validate_file_integrity(f)]

        if not valid_music and not valid_sounds:
            logger.info("No audio files to mix")
            return None

        logger.info(f"Mixing {len(valid_music)} music file(s) and {len(valid_sounds)} sound file(s)")

        # Create music track
        music_track = None
        if valid_music:
            music_track = self._create_music_track(valid_music)

        # Create sound tracks
        sound_tracks = []
        if valid_sounds:
            for sound_file in valid_sounds:
                sound_track = self._create_looping_sound(sound_file)
                sound_tracks.append(sound_track)

        # Mix all tracks together
        if music_track and sound_tracks:
            return self._mix_tracks(music_track, sound_tracks)
        elif music_track:
            return music_track
        elif sound_tracks:
            return self._mix_tracks(None, sound_tracks)
        else:
            return None

    def _create_music_track(self, music_files: List[Path]) -> Path:
        """
        Create music track by combining and looping music files.

        Args:
            music_files: List of music file paths

        Returns:
            Path to processed music track
        """
        # Shuffle if requested
        if self.config.music_shuffle:
            music_files = music_files.copy()
            random.shuffle(music_files)
            logger.info("Shuffled music files")

        logger.info(f"Creating music track from {len(music_files)} file(s)")

        # Get total duration of all music
        music_durations = [self._get_audio_duration(f) for f in music_files]
        total_duration = sum(music_durations)

        logger.info(f"Total music duration: {total_duration:.2f}s, Target: {self.config.duration}s")

        # Determine how many times to loop
        if total_duration < self.config.duration:
            loops_needed = int(self.config.duration / total_duration) + 1
            logger.info(f"Looping music sequence {loops_needed} times")
            final_music = music_files * loops_needed
        else:
            final_music = music_files

        # Concatenate music files
        if len(final_music) == 1:
            concatenated = self._process_single_audio(final_music[0])
        else:
            concatenated = self._concatenate_audio(final_music)

        # Loop to exact duration
        looped = self._loop_audio_to_duration(concatenated, self.config.duration)

        # Apply volume and fades
        output = self._apply_music_effects(looped)

        return output

    def _create_looping_sound(self, sound_file: Path) -> Path:
        """
        Create looping sound track.

        Args:
            sound_file: Path to sound file

        Returns:
            Path to looped sound track
        """
        logger.info(f"Creating looping sound: {sound_file.name}")

        # Loop to duration
        looped = self._loop_audio_to_duration(sound_file, self.config.duration)

        # Apply volume
        output = get_temp_file(self.config, '.mp3')

        cmd = [
            'ffmpeg',
            '-i', str(looped),
            '-filter:a', f'volume={self.config.sounds_volume}',
            '-c:a', 'libmp3lame',
            '-b:a', '192k',
            '-y',
            str(output)
        ]

        self._run_ffmpeg(cmd)
        return output

    def _get_audio_duration(self, audio_path: Path) -> float:
        """
        Get duration of an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.error(f"Failed to get duration for {audio_path}: {e}")
            raise

    def _process_single_audio(self, audio_path: Path) -> Path:
        """
        Process a single audio file (normalize format).

        Args:
            audio_path: Path to audio file

        Returns:
            Path to processed audio
        """
        output_file = get_temp_file(self.config, '.mp3')

        cmd = [
            'ffmpeg',
            '-i', str(audio_path),
            '-c:a', 'libmp3lame',
            '-b:a', '192k',
            '-y',
            str(output_file)
        ]

        self._run_ffmpeg(cmd)
        return output_file

    def _concatenate_audio(self, audio_paths: List[Path]) -> Path:
        """
        Concatenate multiple audio files with crossfade.

        Args:
            audio_paths: List of audio file paths

        Returns:
            Path to concatenated audio
        """
        logger.info(f"Concatenating {len(audio_paths)} audio files")

        # Create concat file
        concat_file = get_temp_file(self.config, '.txt')
        with open(concat_file, 'w') as f:
            for audio in audio_paths:
                f.write(f"file '{audio.absolute()}'\n")

        output_file = get_temp_file(self.config, '.mp3')

        # Simple concatenation
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c:a', 'libmp3lame',
            '-b:a', '192k',
            '-y',
            str(output_file)
        ]

        self._run_ffmpeg(cmd)
        return output_file

    def _loop_audio_to_duration(self, audio_path: Path, duration: float) -> Path:
        """
        Loop audio file to match target duration.

        Args:
            audio_path: Path to audio file
            duration: Target duration in seconds

        Returns:
            Path to looped audio
        """
        output_file = get_temp_file(self.config, '.mp3')

        cmd = [
            'ffmpeg',
            '-stream_loop', '-1',  # Loop infinitely
            '-i', str(audio_path),
            '-t', str(duration),
            '-c:a', 'libmp3lame',
            '-b:a', '192k',
            '-y',
            str(output_file)
        ]

        self._run_ffmpeg(cmd)
        return output_file

    def _apply_music_effects(self, audio_path: Path) -> Path:
        """
        Apply volume and fade effects to music track.

        Args:
            audio_path: Path to audio file

        Returns:
            Path to processed audio
        """
        output_file = get_temp_file(self.config, '.mp3')

        # Apply volume, fade in (2s), fade out (2s)
        fade_duration = 2.0
        audio_duration = self._get_audio_duration(audio_path)
        fade_out_start = max(0, audio_duration - fade_duration)

        filter_str = f'volume={self.config.music_volume},afade=t=in:st=0:d={fade_duration},afade=t=out:st={fade_out_start}:d={fade_duration}'

        cmd = [
            'ffmpeg',
            '-i', str(audio_path),
            '-filter:a', filter_str,
            '-c:a', 'libmp3lame',
            '-b:a', '192k',
            '-y',
            str(output_file)
        ]

        self._run_ffmpeg(cmd)
        return output_file

    def _mix_tracks(self, music_track: Optional[Path], sound_tracks: List[Path]) -> Path:
        """
        Mix music and sound tracks together.

        Args:
            music_track: Path to music track (or None)
            sound_tracks: List of sound track paths

        Returns:
            Path to mixed audio
        """
        logger.info("Mixing audio tracks together")

        output_file = get_temp_file(self.config, '.mp3')

        # Build input arguments
        inputs = []
        if music_track:
            inputs.extend(['-i', str(music_track)])
        for sound_track in sound_tracks:
            inputs.extend(['-i', str(sound_track)])

        # Build filter complex for mixing
        num_inputs = len(inputs) // 2
        if num_inputs == 1:
            # Only one track, no mixing needed
            cmd = [
                'ffmpeg',
                *inputs,
                '-c:a', 'libmp3lame',
                '-b:a', '192k',
                '-y',
                str(output_file)
            ]
        else:
            # Mix all tracks
            filter_inputs = ''.join([f'[{i}:a]' for i in range(num_inputs)])
            filter_complex = f'{filter_inputs}amix=inputs={num_inputs}:duration=first:dropout_transition=2[aout]'

            cmd = [
                'ffmpeg',
                *inputs,
                '-filter_complex', filter_complex,
                '-map', '[aout]',
                '-c:a', 'libmp3lame',
                '-b:a', '192k',
                '-y',
                str(output_file)
            ]

        self._run_ffmpeg(cmd)
        return output_file

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
            raise RuntimeError(f"Audio processing failed: {e}")
