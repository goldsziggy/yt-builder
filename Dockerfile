# YouTube Video Builder Docker Image
FROM python:3.11-slim

# Set metadata
LABEL maintainer="YouTube Video Builder"
LABEL description="Docker image for creating looping YouTube videos with music, sounds, and quotes"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    # Additional dependencies for Pillow
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff-dev \
    libwebp-dev \
    # Font packages for quote rendering
    fonts-dejavu-core \
    fonts-liberation \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app directory
WORKDIR /app

# Copy requirements first for better Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY yt-builder.py .
COPY src/ ./src/

# Create directories for media files
RUN mkdir -p videos music quotes sounds .tmp

# Create a non-root user to run the application
RUN useradd -m -u 1000 videobuilder && \
    chown -R videobuilder:videobuilder /app

# Switch to non-root user
USER videobuilder

# Set the entrypoint
ENTRYPOINT ["python", "yt-builder.py"]

# Default command (show help)
CMD ["--help"]
