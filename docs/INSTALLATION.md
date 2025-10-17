# Soundlab Φ-Matrix - Installation Guide

## Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows 10/11
- **CPU**: 2+ cores recommended
- **Memory**: 4 GB RAM minimum, 8 GB recommended
- **Python**: 3.11 or later
- **Audio**: ASIO-compatible audio interface (optional but recommended)

### Software Dependencies
- Python 3.11+
- Docker (optional, for containerized deployment)
- Git (for source installation)

## Installation Methods

### Method 1: Docker (Recommended for Production)

#### Quick Start

```bash
# Pull the image
docker pull soundlab/phi-matrix:0.9.0-rc1

# Run the container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/logs:/app/logs \
  --name soundlab-phi-matrix \
  soundlab/phi-matrix:0.9.0-rc1
```

#### Using Docker Compose

```bash
# Download docker-compose.staging.yml
wget https://raw.githubusercontent.com/soundlab/phi-matrix/main/docker-compose.staging.yml

# Start the stack
docker-compose -f docker-compose.staging.yml up -d

# Check logs
docker-compose -f docker-compose.staging.yml logs -f
```

#### Health Check

```bash
# Verify the service is healthy
curl http://localhost:8000/healthz

# Check readiness
curl http://localhost:8000/readyz

# View metrics
curl http://localhost:8000/metrics
```

### Method 2: From Release Bundle

#### Download Release

```bash
# Download the latest release
wget https://github.com/soundlab/phi-matrix/releases/download/v0.9.0-rc1/soundlab-0.9.0-rc1.tar.gz

# Extract
tar -xzf soundlab-0.9.0-rc1.tar.gz
cd soundlab-0.9.0-rc1
```

#### Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r server/requirements.txt
```

#### Start Server

```bash
# Navigate to server directory
cd server

# Start with uvicorn
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Or use the provided script (if available)
python main.py
```

### Method 3: From Source (Development)

#### Clone Repository

```bash
git clone https://github.com/soundlab/phi-matrix.git
cd phi-matrix
git checkout v0.9.0-rc1
```

#### Install Dependencies

```bash
# Using make (if available)
make install

# Or manually
pip install -r server/requirements.txt
```

#### Run Development Server

```bash
cd server
python main.py
```

#### Run with Makefile

```bash
# Build release candidate
make rc

# Run tests
make test

# Run validation
make validate

# Build Docker image
make docker-build

# Deploy to staging
make deploy-staging
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Server Configuration
SOUNDLAB_ENV=production
SOUNDLAB_PORT=8000
SOUNDLAB_LOG_LEVEL=info

# Audio Configuration
SOUNDLAB_SAMPLE_RATE=48000
SOUNDLAB_BUFFER_SIZE=512

# Feature Flags
SOUNDLAB_ENABLE_CORS=true
SOUNDLAB_ENABLE_ADAPTIVE_SCALING=true
SOUNDLAB_ENABLE_CHROMATIC=true

# Performance Tuning
SOUNDLAB_MAX_CONNECTIONS=100
SOUNDLAB_TARGET_FPS=30
```

### Configuration Files

#### Performance Profile

Edit `server/config/performance_profile.json`:

```json
{
  "target_fps": 45,
  "audio_buffer_ms": 10,
  "visual_complexity_level": 5,
  "enable_phi_breathing": true,
  "enable_topology_links": true,
  "enable_gradients": true,
  "render_resolution": 1.0
}
```

#### Preset Configuration

Presets are stored in `server/presets/` directory. You can add custom presets as JSON files.

## Post-Installation

### Verify Installation

```bash
# Check version
curl http://localhost:8000/version

# Check health
curl http://localhost:8000/healthz

# Check API status
curl http://localhost:8000/api/status
```

### Run Smoke Tests

```bash
# Health endpoints
python smoke/smoke_health.py

# WebSocket connectivity
python smoke/smoke_websocket.py

# Metrics streaming
python smoke/smoke_metrics.py
```

### Access Dashboard

Open your browser and navigate to:
- Main interface: http://localhost:8000
- Φ-Matrix Dashboard: http://localhost:8000/static/phi-matrix-dashboard.html
- Chromatic Visualizer: http://localhost:8000/static/chromatic-visualizer.html
- API Documentation: http://localhost:8000/docs

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process or use a different port
uvicorn main:app --port 8001
```

### Audio Device Not Found

1. Check available audio devices:
   ```python
   import sounddevice as sd
   print(sd.query_devices())
   ```

2. Set default device in code or via environment variable

### Permission Errors

```bash
# Docker: Run with appropriate user
docker run --user $(id -u):$(id -g) ...

# File permissions
sudo chown -R $USER:$USER logs/ server/config/
```

### Memory Issues

```bash
# Increase Docker memory limit
docker run -m 4g ...

# Adjust Python memory settings
export PYTHONMALLOC=malloc
```

## Uninstallation

### Docker

```bash
# Stop and remove container
docker-compose -f docker-compose.staging.yml down

# Remove image
docker rmi soundlab/phi-matrix:0.9.0-rc1

# Clean up volumes
docker volume rm soundlab-logs soundlab-config
```

### Source/Bundle

```bash
# Deactivate virtual environment
deactivate

# Remove installation directory
rm -rf soundlab-0.9.0-rc1/
```

## Next Steps

- See [OPERATIONS.md](OPERATIONS.md) for operational procedures
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- See [RUNBOOK.md](RUNBOOK.md) for deployment and rollback procedures
