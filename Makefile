.PHONY: help build run shell clean test dry-run stop prune info

# Default target
help:
	@echo "YouTube Video Builder - Makefile Commands"
	@echo ""
	@echo "Setup & Build:"
	@echo "  make build         - Build the Docker image"
	@echo "  make rebuild       - Rebuild the Docker image without cache"
	@echo ""
	@echo "Run Commands:"
	@echo "  make run           - Run with default test parameters"
	@echo "  make dry-run       - Preview configuration without rendering"
	@echo "  make shell         - Open a shell inside the container"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Create a quick 30-second test video"
	@echo "  make test-hq       - Create a high-quality test video"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         - Clean temporary files and output"
	@echo "  make stop          - Stop all running containers"
	@echo "  make prune         - Remove Docker image and clean up"
	@echo "  make info          - Show Docker and system info"
	@echo ""
	@echo "Examples:"
	@echo "  make run ARGS='--duration 300 -o /app/output/custom.mp4'"
	@echo "  ./run-docker.sh --duration 60 --quotes-duration 5 -o /app/output/video.mp4"

# Build the Docker image
build:
	@echo "Building Docker image..."
	docker-compose build

# Rebuild without cache
rebuild:
	@echo "Rebuilding Docker image (no cache)..."
	docker-compose build --no-cache

# Run with custom arguments (use: make run ARGS="--duration 60 ...")
run:
	@echo "Running yt-builder..."
	docker-compose run --rm yt-builder $(ARGS)

# Quick test - 30 second video
test:
	@echo "Creating 30-second test video..."
	docker-compose run --rm yt-builder \
		--duration 30 \
		--quotes-duration 3 \
		--quotes-min-between 5 \
		--quotes-max-between 10 \
		--resolution 1280x720 \
		-o /app/output/test_30s.mp4 \
		--verbose

# High quality test - 1 minute video
test-hq:
	@echo "Creating high-quality 1-minute test video..."
	docker-compose run --rm yt-builder \
		--duration 60 \
		--quotes-duration 5 \
		--quotes-min-between 10 \
		--quotes-max-between 20 \
		--resolution 1920x1080 \
		--fps 30 \
		--music-volume 0.7 \
		--sounds-volume 0.5 \
		-o /app/output/test_hq.mp4 \
		--verbose

# Dry run to preview configuration
dry-run:
	@echo "Running dry-run (preview only)..."
	docker-compose run --rm yt-builder \
		--duration 300 \
		--quotes-duration 5 \
		--quotes-min-between 10 \
		--quotes-max-between 30 \
		--dry-run

# Open shell inside container
shell:
	@echo "Opening shell in container..."
	docker-compose run --rm --entrypoint /bin/bash yt-builder

# Clean temporary and output files
clean:
	@echo "Cleaning temporary files and output..."
	rm -rf .tmp/*
	rm -rf output/*
	@echo "Clean complete!"

# Stop all running containers
stop:
	@echo "Stopping containers..."
	docker-compose down

# Remove Docker image and clean up
prune:
	@echo "Removing Docker image and cleaning up..."
	docker-compose down
	docker rmi yt-builder:latest 2>/dev/null || true
	docker system prune -f
	@echo "Prune complete!"

# Show Docker and system info
info:
	@echo "=== Docker Info ==="
	docker --version
	docker-compose --version
	@echo ""
	@echo "=== Docker Images ==="
	docker images | grep -E "REPOSITORY|yt-builder" || echo "No yt-builder images found"
	@echo ""
	@echo "=== Disk Usage ==="
	docker system df
	@echo ""
	@echo "=== Media Files ==="
	@echo "Videos: $$(ls -1 videos/ 2>/dev/null | wc -l | tr -d ' ') files"
	@echo "Music: $$(ls -1 music/ 2>/dev/null | wc -l | tr -d ' ') files"
	@echo "Quotes: $$(ls -1 quotes/*.txt 2>/dev/null | wc -l | tr -d ' ') files"
	@echo "Sounds: $$(ls -1 sounds/ 2>/dev/null | wc -l | tr -d ' ') files"
	@echo "Output: $$(ls -1 output/ 2>/dev/null | wc -l | tr -d ' ') files"

# Install Python dependencies (for native installation)
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

# Run natively (without Docker)
run-native:
	@echo "Running natively (requires FFmpeg installed)..."
	python yt-builder.py $(ARGS)
