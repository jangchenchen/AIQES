# Multi-stage Dockerfile for QA System

# ============================================================================
# Stage 1: Builder - Install dependencies
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmagic1 \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-web.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements-web.txt

# ============================================================================
# Stage 2: Runtime - Final image
# ============================================================================
FROM python:3.11-slim

LABEL maintainer="your-email@example.com"
LABEL description="QA System - AI-powered quiz and exam platform"
LABEL version="1.0.0"

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash qauser

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/qauser/.local

# Copy application code
COPY --chown=qauser:qauser . .

# Create required directories
RUN mkdir -p data uploads AI_cf logs && \
    chown -R qauser:qauser data uploads AI_cf logs

# Switch to non-root user
USER qauser

# Update PATH
ENV PATH=/home/qauser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web_server.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/api/ai-config')" || exit 1

# Expose port
EXPOSE 5001

# Run migrations and start server
CMD python -m src.database.migrations migrate && \
    python web_server.py
