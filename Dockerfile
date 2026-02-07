FROM python:3.11-slim-bookworm

# Metadata
LABEL maintainer="DockerMate Contributors"
LABEL description="Intelligent Docker Management for Home Labs"
LABEL version="1.0.0"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app user (don't run as root)
RUN useradd -m -u 1000 dockermate

# Create app directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Install certbot for Let's Encrypt (optional)
RUN pip install --no-cache-dir certbot

# Copy application code
COPY --chown=dockermate:dockermate . .

# Create data directories
RUN mkdir -p \
    /app/data/ssl \
    /app/data/backups \
    /app/stacks \
    /app/exports \
    && chown -R dockermate:dockermate /app

# Make entrypoint and scripts executable
RUN chmod +x docker-entrypoint.sh manage.py

# Switch to app user
USER dockermate

# Expose HTTPS port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -fk https://localhost:5000/api/health || exit 1

# Run application via entrypoint (handles migrations and setup)
ENTRYPOINT ["/app/docker-entrypoint.sh"]