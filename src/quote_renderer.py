"""Quote rendering module for YouTube Video Builder"""

import logging
import random
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .validator import get_files_by_format, QUOTE_FORMATS

logger = logging.getLogger(__name__)


class QuoteRenderer:
    """Handles quote rendering and overlay."""

    def __init__(self, config: Config):
        """
        Initialize quote renderer.

        Args:
            config: Configuration object
        """
        self.config = config
        self.quotes = self._load_quotes()

    def _load_quotes(self) -> List[str]:
        """
        Load all quotes from quotes directory.

        Returns:
            List of quote texts
        """
        quote_files = get_files_by_format(self.config.quotes_dir, QUOTE_FORMATS)

        if not quote_files:
            logger.info("No quote files found")
            return []

        quotes = []
        for quote_file in quote_files:
            try:
                with open(quote_file, 'r', encoding='utf-8') as f:
                    quote_text = f.read().strip()
                    if quote_text:
                        quotes.append(quote_text)
                    else:
                        logger.warning(f"Empty quote file: {quote_file}")
            except Exception as e:
                logger.error(f"Failed to read quote file {quote_file}: {e}")

        logger.info(f"Loaded {len(quotes)} quote(s)")
        return quotes

    def generate_quote_timings(self) -> List[Dict[str, Any]]:
        """
        Generate timing information for when quotes should appear.

        Returns:
            List of quote timing dictionaries
        """
        if not self.quotes:
            logger.info("No quotes to display")
            return []

        # Shuffle quotes if requested
        quotes_to_use = self.quotes.copy()
        if self.config.quotes_shuffle:
            random.shuffle(quotes_to_use)
            logger.info("Shuffled quotes")

        timings = []
        current_time = random.uniform(
            self.config.quotes_min_between,
            self.config.quotes_max_between
        )

        quote_index = 0

        while current_time + self.config.quotes_duration <= self.config.duration:
            quote_text = quotes_to_use[quote_index % len(quotes_to_use)]

            timings.append({
                'text': quote_text,
                'start': current_time,
                'end': current_time + self.config.quotes_duration,
                'index': len(timings)
            })

            # Calculate next quote time
            interval = random.uniform(
                self.config.quotes_min_between,
                self.config.quotes_max_between
            )
            current_time += self.config.quotes_duration + interval
            quote_index += 1

        logger.info(f"Generated {len(timings)} quote timing(s)")

        if self.config.verbose:
            for timing in timings:
                logger.debug(
                    f"Quote {timing['index']}: {timing['start']:.2f}s - {timing['end']:.2f}s: "
                    f"{timing['text'][:50]}..."
                )

        return timings

    def render_quote_image(self, quote_text: str, index: int) -> Path:
        """
        Render a quote as an image.

        Args:
            quote_text: The quote text to render
            index: Quote index for filename

        Returns:
            Path to rendered quote image
        """
        width, height = self.config.resolution

        # Create transparent image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Determine font size based on resolution
        font_size = int(height / 20)  # Roughly 5% of height

        # Try to load a nice font, fallback to default
        try:
            # Try to use a system font
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            try:
                # Alternative font locations
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                # Fallback to default
                font = ImageFont.load_default()
                logger.warning("Using default font, text may not look optimal")

        # Calculate text dimensions and wrap text
        max_width = int(width * 0.8)  # 80% of screen width
        wrapped_text = self._wrap_text(quote_text, font, max_width, draw)

        # Calculate text bounding box
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Determine position based on style
        if self.config.quote_style == 'top':
            y_position = int(height * 0.1)
        elif self.config.quote_style == 'bottom':
            y_position = int(height * 0.8 - text_height)
        else:  # centered or minimal
            y_position = int((height - text_height) / 2)

        x_position = int((width - text_width) / 2)

        # Draw semi-transparent background if not minimal style
        if self.config.quote_style != 'minimal':
            padding = 20
            bg_bbox = [
                x_position - padding,
                y_position - padding,
                x_position + text_width + padding,
                y_position + text_height + padding
            ]
            draw.rectangle(bg_bbox, fill=(0, 0, 0, 180))

        # Draw text with outline for better readability
        outline_range = 2
        outline_color = (0, 0, 0, 255)
        text_color = (255, 255, 255, 255)

        # Draw outline
        for x_offset in range(-outline_range, outline_range + 1):
            for y_offset in range(-outline_range, outline_range + 1):
                if x_offset != 0 or y_offset != 0:
                    draw.multiline_text(
                        (x_position + x_offset, y_position + y_offset),
                        wrapped_text,
                        font=font,
                        fill=outline_color,
                        align='center'
                    )

        # Draw main text
        draw.multiline_text(
            (x_position, y_position),
            wrapped_text,
            font=font,
            fill=text_color,
            align='center'
        )

        # Save image
        output_path = self.config.temp_dir / f"quote_{index}.png"
        img.save(output_path)

        return output_path

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.Draw) -> str:
        """
        Wrap text to fit within max width.

        Args:
            text: Text to wrap
            font: Font to use
            max_width: Maximum width in pixels
            draw: ImageDraw object for measuring text

        Returns:
            Wrapped text with newlines
        """
        lines = []
        paragraphs = text.split('\n')

        for paragraph in paragraphs:
            if not paragraph.strip():
                lines.append('')
                continue

            words = paragraph.split()
            current_line = []

            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                test_width = bbox[2] - bbox[0]

                if test_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # Single word is too long, add it anyway
                        lines.append(word)

            if current_line:
                lines.append(' '.join(current_line))

        return '\n'.join(lines)

    def get_drawtext_filter(self, timings: List[Dict[str, Any]]) -> str:
        """
        Generate ffmpeg drawtext filter for overlaying quotes.

        Args:
            timings: List of quote timing dictionaries

        Returns:
            Filter string for ffmpeg
        """
        if not timings:
            return ""

        width, height = self.config.resolution

        # Build drawtext filters
        filters = []
        for timing in timings:
            # Escape text for ffmpeg
            text = timing['text'].replace("'", "\\'").replace(":", "\\:")

            # Determine position
            if self.config.quote_style == 'top':
                y_pos = f'h*0.1'
            elif self.config.quote_style == 'bottom':
                y_pos = f'h*0.8'
            else:  # centered
                y_pos = f'(h-text_h)/2'

            # Build filter with fade in/out
            fade_duration = 0.5
            start_fade_in = timing['start']
            start_fade_out = timing['end'] - fade_duration

            filter_str = (
                f"drawtext="
                f"text='{text}':"
                f"fontsize=h/20:"
                f"fontcolor=white:"
                f"borderw=2:"
                f"bordercolor=black:"
                f"x=(w-text_w)/2:"
                f"y={y_pos}:"
                f"enable='between(t,{timing['start']},{timing['end']})':"
                f"alpha='if(lt(t,{start_fade_in + fade_duration}),(t-{start_fade_in})/{fade_duration},if(gt(t,{start_fade_out}),({timing['end']}-t)/{fade_duration},1))'"
            )
            filters.append(filter_str)

        return ','.join(filters)
