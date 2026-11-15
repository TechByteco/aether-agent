# ==============================================================================
# AETHER + LEON Sovereign 24/7 Cloud Assistant Dockerfile
# Lightweight, high-performance, zero-GPU requirement cloud runtime.
# ==============================================================================

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for efficient Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and data
COPY src/ /app/src/
COPY data/ /app/data/

# Expose server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/owner/health || exit 1

# Start Uvicorn web server + AutonomousOperator lifecycle
CMD ["sh", "-c", "uvicorn aether.web.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
