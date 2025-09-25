# Dockerfile for Mail2printer
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cups-client \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create non-root user
RUN useradd -r -u 1000 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Create volume mount points
VOLUME ["/app/config", "/app/logs"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python main.py --test-email --config /app/config/config.yaml || exit 1

# Default command
CMD ["python", "main.py", "--config", "/app/config/config.yaml"]

# Build instructions:
# docker build -t mail2printer .
#
# Run instructions:
# docker run -d \
#   --name mail2printer \
#   -v $(pwd)/config:/app/config:ro \
#   -v $(pwd)/logs:/app/logs \
#   --restart unless-stopped \
#   mail2printer