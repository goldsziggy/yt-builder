#!/usr/bin/env python3
"""
YouTube Video Builder - Create looping videos with music, sounds, and quotes
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Tuple

from src.validator import validate_inputs
from src.video_processor import VideoProcessor
from src.audio_mixer import AudioMixer
from src.quote_renderer import QuoteRenderer
from src.config import Config
from src.utils import setup_logging, check_disk_space, estimate_output_size


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Create looping videos for YouTube with music, sounds, and quotes.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --duration 600 --quotes-duration 5 --quotes-min-between 10 --quotes-max-between 30
  %(prog)s --duration 300 --music-shuffle --quotes-shuffle -o my_video.mp4 --verbose
        """
    )

    # Required arguments
    parser.add_argument(
        '--duration',
        type=float,
        required=True,
        help='Duration of the output video in seconds'
    )

    # Quote timing arguments
    parser.add_argument(
        '--quotes-duration',
        type=float,
        default=5.0,
        help='How long to show each quote on screen (seconds, default: 5.0)'
    )
    parser.add_argument(
        '--quotes-min-between',
        type=float,
        default=10.0,
        help='Minimum time between quotes (seconds, default: 10.0)'
    )
    parser.add_argument(
        '--quotes-max-between',
        type=float,
        default=30.0,
        help='Maximum time between quotes (seconds, default: 30.0)'
    )

    # Shuffle options
    parser.add_argument(
        '--music-shuffle',
        action='store_true',
        help='Shuffle music files before combining'
    )
    parser.add_argument(
        '--quotes-shuffle',
        action='store_true',
        help='Shuffle quote files before displaying'
    )

    # Output options
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='output.mp4',
        help='Output file path (default: output.mp4)'
    )

    # Video options
    parser.add_argument(
        '--fps',
        type=int,
        default=30,
        help='Frame rate for output video (default: 30)'
    )
    parser.add_argument(
        '--resolution',
        type=str,
        default='1920x1080',
        help='Output resolution in format WIDTHxHEIGHT (default: 1920x1080)'
    )
    parser.add_argument(
        '--transition',
        type=str,
        choices=['none', 'fade', 'crossfade'],
        default='crossfade',
        help='Transition effect between video clips (default: crossfade)'
    )

    # Audio options
    parser.add_argument(
        '--music-volume',
        type=float,
        default=0.7,
        help='Volume level for music track (0.0-1.0, default: 0.7)'
    )
    parser.add_argument(
        '--sounds-volume',
        type=float,
        default=0.5,
        help='Volume level for sound effects (0.0-1.0, default: 0.5)'
    )

    # Quote styling
    parser.add_argument(
        '--quote-style',
        type=str,
        choices=['minimal', 'centered', 'bottom', 'top'],
        default='centered',
        help='Preset quote styling (default: centered)'
    )

    # Utility options
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable detailed logging output'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview configuration without rendering video'
    )

    return parser.parse_args()


def parse_resolution(resolution_str: str) -> Tuple[int, int]:
    """Parse resolution string into width and height."""
    try:
        width, height = resolution_str.lower().split('x')
        return int(width), int(height)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid resolution format: {resolution_str}. Expected WIDTHxHEIGHT")


def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    try:
        # Parse resolution
        width, height = parse_resolution(args.resolution)

        # Create configuration object
        config = Config(
            duration=args.duration,
            music_shuffle=args.music_shuffle,
            quotes_shuffle=args.quotes_shuffle,
            quotes_duration=args.quotes_duration,
            quotes_min_between=args.quotes_min_between,
            quotes_max_between=args.quotes_max_between,
            output_path=args.output,
            fps=args.fps,
            resolution=(width, height),
            music_volume=args.music_volume,
            sounds_volume=args.sounds_volume,
            quote_style=args.quote_style,
            transition=args.transition,
            verbose=args.verbose,
            dry_run=args.dry_run
        )

        # Validate inputs
        logger.info("Validating inputs...")
        validate_inputs(config)

        if args.dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN - Configuration Preview")
            logger.info("=" * 60)
            logger.info(f"Duration: {config.duration}s")
            logger.info(f"Resolution: {width}x{height}")
            logger.info(f"FPS: {config.fps}")
            logger.info(f"Output: {config.output_path}")
            logger.info(f"Music Shuffle: {config.music_shuffle}")
            logger.info(f"Quotes Shuffle: {config.quotes_shuffle}")
            logger.info(f"Quote Duration: {config.quotes_duration}s")
            logger.info(f"Quote Interval: {config.quotes_min_between}s - {config.quotes_max_between}s")
            logger.info(f"Music Volume: {config.music_volume}")
            logger.info(f"Sounds Volume: {config.sounds_volume}")
            logger.info(f"Quote Style: {config.quote_style}")
            logger.info(f"Transition: {config.transition}")
            logger.info("=" * 60)
            logger.info("No video will be rendered in dry-run mode.")
            return 0

        # Check disk space
        estimated_size = estimate_output_size(config)
        check_disk_space(Path(config.output_path).parent, estimated_size)

        # Initialize processors
        logger.info("Initializing video processor...")
        video_processor = VideoProcessor(config)

        logger.info("Initializing audio mixer...")
        audio_mixer = AudioMixer(config)

        logger.info("Initializing quote renderer...")
        quote_renderer = QuoteRenderer(config)

        # Process video
        logger.info("=" * 60)
        logger.info("Starting video generation...")
        logger.info("=" * 60)

        # Step 1: Combine and loop videos
        logger.info("Step 1/4: Processing video clips...")
        video_file = video_processor.process_videos()

        # Step 2: Mix audio tracks
        logger.info("Step 2/4: Mixing audio tracks...")
        audio_file = audio_mixer.mix_audio()

        # Step 3: Render quotes
        logger.info("Step 3/4: Rendering quotes...")
        quote_timings = quote_renderer.generate_quote_timings()

        # Step 4: Combine everything
        logger.info("Step 4/4: Combining video, audio, and quotes...")
        video_processor.combine_all(video_file, audio_file, quote_timings, quote_renderer)

        logger.info("=" * 60)
        logger.info(f"Video successfully created: {config.output_path}")
        logger.info("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.error("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Detailed error information:")
        return 1


if __name__ == '__main__':
    sys.exit(main())
