# Multi-stage Dockerfile for Obscura Enchanted Agent Engine
FROM python:3.11-slim as runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=9222

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run unit test validation during build
RUN python run_tests.py

EXPOSE 9222 8000

# Default: start Model Context Protocol stdio server or HTTP daemon
CMD ["python", "-m", "obscura_engine.cli", "serve"]
