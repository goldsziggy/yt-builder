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
        self._font_cache = {}  # Cache loaded fonts

    def _load_quotes(self) -> List[str]:
        """
        Load all quotes from quotes directory.
        - Ignores files with 'example' in the filename
        - Supports multiple quotes per file (enclosed in double quotes)
        - Falls back to treating entire file as single quote if no quotes found

        Returns:
            List of quote texts
        """
        quote_files = get_files_by_format(self.config.quotes_dir, QUOTE_FORMATS)

        if not quote_files:
            logger.info("No quote files found")
            return []

        quotes = []
        for quote_file in quote_files:
            # Skip files with 'example' in the filename
            if 'example' in quote_file.name.lower():
                logger.debug(f"Skipping example file: {quote_file.name}")
                continue

            try:
                with open(quote_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                    if not content:
                        logger.warning(f"Empty quote file: {quote_file}")
                        continue

                    # Try to parse as multiple quotes (enclosed in double quotes)
                    parsed_quotes = self._parse_quotes_all(content, quote_file)

                    if parsed_quotes:
                        # Found quotes enclosed in double quotes
                        quotes.extend(parsed_quotes)
                    else:
                        # No double quotes found - treat entire file as single quote
                        # This provides backwards compatibility
                        quotes.append(content)
                        logger.debug(f"Loaded single quote from {quote_file.name}")

            except UnicodeDecodeError as e:
                logger.warning(f"Skipping file with encoding issue: {quote_file.name}")
            except Exception as e:
                logger.error(f"Failed to read quote file {quote_file}: {e}")

        logger.info(f"Loaded {len(quotes)} quote(s)")
        return quotes

    def _parse_quotes_all(self, content: str, file_path: Path) -> List[str]:
        """
        Parse file content to extract multiple quotes.
        Each quote should be enclosed in double quotes.
        Returns empty list if no quotes found (for backwards compatibility).

        Args:
            content: File content
            file_path: Path to file (for logging)

        Returns:
            List of parsed quotes (empty if no double-quoted strings found)
        """
        quotes = []
        in_quote = False
        current_quote = []
        i = 0

        while i < len(content):
            char = content[i]

            if char == '"':
                if in_quote:
                    # End of quote
                    quote_text = ''.join(current_quote).strip()
                    if quote_text:
                        quotes.append(quote_text)
                        logger.debug(f"Parsed quote from {file_path.name}: {quote_text[:50]}...")
                    current_quote = []
                    in_quote = False
                else:
                    # Start of quote
                    in_quote = True
                i += 1
            elif char == '\\' and i + 1 < len(content) and content[i + 1] == '"':
                # Escaped quote - include it in the quote text
                if in_quote:
                    current_quote.append('"')
                i += 2
            else:
                if in_quote:
                    current_quote.append(char)
                i += 1

        if in_quote:
            logger.warning(f"Unclosed quote in {file_path.name}")

        if quotes:
            logger.info(f"Parsed {len(quotes)} quote(s) from {file_path.name}")

        return quotes

    def _load_font(self, font_size: int) -> ImageFont.ImageFont:
        """
        Load font based on configuration.

        Args:
            font_size: Font size in pixels

        Returns:
            ImageFont object
        """
        font_config = self.config.quote_font

        # Check cache first
        cache_key = (font_config, font_size)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font = None

        # If font_config is 'default', use system defaults
        if font_config == 'default':
            font = self._load_default_font(font_size)
        # If it's a path to a file
        elif Path(font_config).exists() and Path(font_config).suffix.lower() in ['.ttf', '.ttc', '.otf']:
            try:
                font = ImageFont.truetype(font_config, font_size)
                logger.info(f"Loaded custom font: {font_config}")
            except Exception as e:
                logger.warning(f"Failed to load font from {font_config}: {e}. Using default.")
                font = self._load_default_font(font_size)
        # Try as a font name (common font names)
        else:
            font = self._load_font_by_name(font_config, font_size)

        # Cache the font
        self._font_cache[cache_key] = font
        return font

    def _load_default_font(self, font_size: int) -> ImageFont.ImageFont:
        """
        Load default system font.

        Args:
            font_size: Font size in pixels

        Returns:
            ImageFont object
        """
        try:
            # Try to use a system font (macOS)
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            try:
                # Alternative font locations (Linux)
                return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                # Fallback to default
                logger.warning("Using default PIL font, text may not look optimal")
                return ImageFont.load_default()

    def _load_font_by_name(self, font_name: str, font_size: int) -> ImageFont.ImageFont:
        """
        Load font by common name.

        Args:
            font_name: Font name (e.g., 'Arial', 'Helvetica', 'Times New Roman')
            font_size: Font size in pixels

        Returns:
            ImageFont object
        """
        # Common font locations by OS
        font_paths = []

        # First check local fonts/ directory (for custom fonts like TenPounds)
        font_paths.extend([
            f"fonts/{font_name}.ttf",
            f"fonts/{font_name}.ttc",
            f"fonts/{font_name}.otf",
            # Also try lowercase
            f"fonts/{font_name.lower()}.ttf",
            f"fonts/{font_name.lower()}.ttc",
            f"fonts/{font_name.lower()}.otf",
        ])

        # macOS font paths
        font_paths.extend([
            f"/System/Library/Fonts/{font_name}.ttc",
            f"/System/Library/Fonts/{font_name}.ttf",
            f"/Library/Fonts/{font_name}.ttf",
            f"/Library/Fonts/{font_name}.ttc",
        ])

        # Linux font paths
        font_paths.extend([
            f"/usr/share/fonts/truetype/{font_name.lower()}/{font_name}.ttf",
            f"/usr/share/fonts/truetype/{font_name.lower()}-bold/{font_name}-Bold.ttf",
            f"/usr/share/fonts/TTF/{font_name}.ttf",
        ])

        # Windows font paths
        font_paths.extend([
            f"C:/Windows/Fonts/{font_name}.ttf",
            f"C:/Windows/Fonts/{font_name}.ttc",
        ])

        # Try each path
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    logger.info(f"Loaded font by name '{font_name}' from: {font_path}")
                    return font
                except Exception as e:
                    logger.debug(f"Failed to load font from {font_path}: {e}")

        # If no font found, use default
        logger.warning(f"Could not find font '{font_name}', using default")
        return self._load_default_font(font_size)

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

        # Load font based on configuration
        font = self._load_font(font_size)

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

    def _get_font_file_path(self) -> str:
        """
        Get the absolute path to the font file for ffmpeg.

        Returns:
            Absolute path to font file, or empty string if using default
        """
        font_config = self.config.quote_font

        # If it's already a path to an existing file
        if Path(font_config).exists() and Path(font_config).suffix.lower() in ['.ttf', '.ttc', '.otf']:
            return str(Path(font_config).absolute())

        # Check fonts/ directory
        font_paths = [
            f"fonts/{font_config}.ttf",
            f"fonts/{font_config.lower()}.ttf",
            f"fonts/{font_config}.ttc",
            f"fonts/{font_config}.otf",
        ]

        for font_path in font_paths:
            if Path(font_path).exists():
                return str(Path(font_path).absolute())

        # Try system fonts for common names
        system_font_paths = []

        # macOS
        system_font_paths.extend([
            f"/System/Library/Fonts/{font_config}.ttc",
            f"/System/Library/Fonts/{font_config}.ttf",
            f"/Library/Fonts/{font_config}.ttf",
        ])

        # Linux
        system_font_paths.extend([
            f"/usr/share/fonts/truetype/{font_config.lower()}/{font_config}.ttf",
            f"/usr/share/fonts/TTF/{font_config}.ttf",
        ])

        for font_path in system_font_paths:
            if Path(font_path).exists():
                return str(Path(font_path).absolute())

        # Return empty string to use ffmpeg default
        logger.warning(f"Font '{font_config}' not found, ffmpeg will use default font")
        return ""

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

        # Get font file path
        font_file = self._get_font_file_path()

        if font_file:
            logger.info(f"Using custom font for quotes: {font_file}")
        else:
            logger.info("Using default system font for quotes")

        # Build drawtext filters
        filters = []
        for timing in timings:
            # Wrap text to fit within 80% of screen width
            wrapped_text = self._wrap_text_for_ffmpeg(timing['text'], width)

            # Escape text for ffmpeg
            text = wrapped_text.replace("'", "\\'").replace(":", "\\:")

            # Determine position
            if self.config.quote_style == 'top':
                y_pos = f'h*0.1'
            elif self.config.quote_style == 'bottom':
                y_pos = f'h*0.85-text_h'
            else:  # centered
                y_pos = f'(h-text_h)/2'

            # Build filter with fade in/out
            fade_duration = 0.5
            start_fade_in = timing['start']
            start_fade_out = timing['end'] - fade_duration

            # Build filter string
            filter_parts = [
                f"drawtext=text='{text}'",
            ]

            # Add font file if available
            if font_file:
                # Escape colons in the font path for ffmpeg
                escaped_font_path = font_file.replace(':', '\\:')
                filter_parts.append(f"fontfile='{escaped_font_path}'")

            # Add remaining parameters
            filter_parts.extend([
                "fontsize=h/20",
                "fontcolor=white",
                "borderw=2",
                "bordercolor=black",
                "x=(w-text_w)/2",
                f"y={y_pos}",
                f"enable='between(t,{timing['start']},{timing['end']})'",
                f"alpha='if(lt(t,{start_fade_in + fade_duration}),(t-{start_fade_in})/{fade_duration},if(gt(t,{start_fade_out}),({timing['end']}-t)/{fade_duration},1))'"
            ])

            filter_str = ':'.join(filter_parts)
            filters.append(filter_str)

        return ','.join(filters)

    def _wrap_text_for_ffmpeg(self, text: str, screen_width: int) -> str:
        """
        Wrap text for ffmpeg drawtext filter.
        Uses newlines to break text into multiple lines.

        Args:
            text: Text to wrap
            screen_width: Screen width in pixels

        Returns:
            Text with newlines for wrapping
        """
        # Calculate approximate character limit per line
        # Font size is h/20, and we want text to fit in 80% of width
        # Rough estimate: each character is about fontsize/2 pixels wide
        max_width = int(screen_width * 0.8)
        font_size = screen_width / 1920 * 54  # Approximate font size for 1080p
        chars_per_line = int(max_width / (font_size * 0.6))  # 0.6 is average char width ratio

        # Ensure minimum chars per line
        chars_per_line = max(chars_per_line, 20)

        # Split text into words
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)

            # Check if adding this word would exceed the limit
            if current_length + word_length + len(current_line) > chars_per_line and current_line:
                # Start a new line
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                # Add word to current line
                current_line.append(word)
                current_length += word_length

        # Add the last line
        if current_line:
            lines.append(' '.join(current_line))

        # Join lines with newline character for ffmpeg
        return '\n'.join(lines)
