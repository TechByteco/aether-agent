# AETHER 24/7 Sovereign Cloud Consciousness Container
# Optimized for 100% Free Cloud Platforms (HuggingFace Spaces, Render, Docker)
FROM python:3.11-slim

WORKDIR /app

# System essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy AETHER source code, static UI, and consciousness snapshot
COPY app.py .
COPY static ./static
COPY data ./data

EXPOSE 7860
EXPOSE 8000

ENV PORT=7860
ENV AETHER_CLOUD_MODE=true

CMD ["python", "app.py"]
