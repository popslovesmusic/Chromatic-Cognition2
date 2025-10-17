# Soundlab Φ-Matrix - Production Dockerfile
# Feature 019: Release Readiness Validation

# Build arguments
ARG PYTHON_VERSION=3.11
ARG VERSION=0.9.0-rc1
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

#==============================================================================
# Base Stage - Python runtime
#==============================================================================
FROM python:${PYTHON_VERSION}-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 soundlab && \
    mkdir -p /app /app/logs /app/config && \
    chown -R soundlab:soundlab /app

#==============================================================================
# Dependencies Stage - Install Python packages
#==============================================================================
FROM base as dependencies

WORKDIR /app

# Copy requirements
COPY server/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

#==============================================================================
# Production Stage - Final image
#==============================================================================
FROM base as production

WORKDIR /app

# Copy Python dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=soundlab:soundlab server/ /app/server/
COPY --chown=soundlab:soundlab static/ /app/static/

# Copy configuration and docs
COPY --chown=soundlab:soundlab docs/ /app/docs/ 2>/dev/null || true

# Set version metadata
ARG VERSION
ARG GIT_COMMIT
ARG BUILD_DATE

ENV SOUNDLAB_VERSION=${VERSION} \
    SOUNDLAB_COMMIT=${GIT_COMMIT} \
    SOUNDLAB_BUILD_DATE=${BUILD_DATE}

# Add version file
RUN echo "VERSION=${VERSION}" > /app/version.txt && \
    echo "GIT_COMMIT=${GIT_COMMIT}" >> /app/version.txt && \
    echo "BUILD_DATE=${BUILD_DATE}" >> /app/version.txt

# Labels
LABEL org.opencontainers.image.title="Soundlab Φ-Matrix" \
      org.opencontainers.image.description="Real-time audio processing with Φ-modulation and consciousness metrics" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.licenses="MIT"

# Switch to app user
USER soundlab

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/healthz', timeout=5)" || exit 1

# Set working directory
WORKDIR /app/server

# Default command - run with uvicorn
CMD ["python", "-m", "uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--log-level", "info", \
     "--access-log", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
