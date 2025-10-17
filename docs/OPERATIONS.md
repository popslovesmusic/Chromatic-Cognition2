# Soundlab Φ-Matrix - Operations Guide

## Overview

This guide covers day-to-day operations of the Soundlab Φ-Matrix system.

## Monitoring

### Health Checks

#### Liveness Check
```bash
curl http://localhost:8000/healthz
```

Expected response:
```json
{
  "status": "healthy",
  "service": "soundlab-phi-matrix",
  "version": "0.9.0-rc1"
}
```

#### Readiness Check
```bash
curl http://localhost:8000/readyz
```

Expected response when ready:
```json
{
  "status": "ready",
  "checks": {
    "audio_server": true,
    "metrics_streamer": true,
    "state_sync_manager": true,
    "adaptive_enabled": true,
    "cpu_available": true,
    "memory_available": true
  }
}
```

### Performance Metrics

#### Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

Key metrics:
- `soundlab_audio_running` - Audio server status (0/1)
- `soundlab_callback_count` - Total audio callbacks processed
- `soundlab_metrics_clients` - Connected metrics clients
- `soundlab_websocket_clients` - Connected WebSocket clients
- `soundlab_websocket_latency_avg_ms` - Average WebSocket latency
- `soundlab_cpu_percent` - CPU usage
- `soundlab_memory_percent` - Memory usage
- `soundlab_phi_depth` - Current Φ depth
- `soundlab_phi_phase` - Current Φ phase

#### API Status
```bash
curl http://localhost:8000/api/status
```

#### Dashboard State
```bash
curl http://localhost:8000/api/dashboard/state
```

#### Latency Statistics
```bash
curl http://localhost:8000/api/dashboard/latency
```

### Logs

#### Docker Logs
```bash
# Follow logs
docker logs -f soundlab-phi-matrix

# Last 100 lines
docker logs --tail 100 soundlab-phi-matrix

# With timestamps
docker logs -t soundlab-phi-matrix
```

#### File Logs
```bash
# Application logs
tail -f logs/soundlab.log

# Access logs
tail -f logs/access.log

# Error logs
tail -f logs/error.log
```

## Performance Tuning

### Check Current Performance

```bash
# Get performance profile
cat server/config/performance_profile.json

# Run benchmark
cd server
python benchmark_runner.py

# Check adaptive scaling stats
curl http://localhost:8000/api/dashboard/sync-health
```

### Adjust Visual Complexity

The adaptive scaler automatically adjusts, but you can manually set targets:

```bash
# Edit performance profile
nano server/config/performance_profile.json

# Restart to apply
docker-compose restart soundlab
```

### Audio Buffer Tuning

For lower latency (may increase CPU):
```json
{
  "audio_buffer_ms": 5
}
```

For stability (may increase latency):
```json
{
  "audio_buffer_ms": 20
}
```

### FPS Tuning

```json
{
  "target_fps": 30,  // Conservative
  "target_fps": 45,  // Balanced
  "target_fps": 60   // High performance
}
```

## Session Management

### Recording Sessions

#### Start Recording
```bash
curl -X POST http://localhost:8000/api/recorder/start
```

#### Stop Recording
```bash
curl -X POST http://localhost:8000/api/recorder/stop
```

#### List Sessions
```bash
curl http://localhost:8000/api/recorder/sessions
```

#### Retrieve Session
```bash
curl http://localhost:8000/api/recorder/sessions/{session_id}
```

### Preset Management

#### List Presets
```bash
curl http://localhost:8000/api/presets
```

#### Load Preset
```bash
curl -X POST http://localhost:8000/api/preset/load -H "Content-Type: application/json" -d '{"preset_id": "golden_ratio"}'
```

#### Save Preset
```bash
curl -X POST http://localhost:8000/api/preset/save -H "Content-Type: application/json" -d '{
  "name": "custom_preset",
  "phi_depth": 1.2,
  "phi_phase": 0.5
}'
```

## Backup and Restore

### Backup Configuration

```bash
# Backup configs
tar -czf backup-config-$(date +%Y%m%d).tar.gz server/config/

# Backup presets
tar -czf backup-presets-$(date +%Y%m%d).tar.gz server/presets/

# Backup sessions
tar -czf backup-sessions-$(date +%Y%m%d).tar.gz server/sessions/
```

### Restore Configuration

```bash
# Restore configs
tar -xzf backup-config-20251017.tar.gz -C server/

# Restart service
docker-compose restart soundlab
```

### Data Export

```bash
# Export session data
curl -X POST http://localhost:8000/api/export/session/{session_id} -o session.json

# Export all sessions
curl http://localhost:8000/api/export/all -o all_sessions.tar.gz
```

## Scaling

### Horizontal Scaling (Multiple Instances)

For load balancing across multiple backend instances:

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  soundlab:
    image: soundlab/phi-matrix:0.9.0-rc1
    deploy:
      replicas: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - soundlab
```

```bash
docker-compose -f docker-compose.scale.yml up -d --scale soundlab=3
```

### Vertical Scaling (Resource Limits)

```yaml
services:
  soundlab:
    image: soundlab/phi-matrix:0.9.0-rc1
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Maintenance

### Routine Maintenance Checklist

**Daily:**
- [ ] Check health endpoints
- [ ] Review error logs
- [ ] Monitor CPU/Memory usage
- [ ] Verify WebSocket connections

**Weekly:**
- [ ] Review performance metrics
- [ ] Check disk space
- [ ] Backup configurations
- [ ] Review and archive old sessions

**Monthly:**
- [ ] Update dependencies (if patches available)
- [ ] Run full benchmark suite
- [ ] Review and optimize performance profile
- [ ] Validate backups

### Update Procedure

1. **Backup current state**
   ```bash
   make backup  # If available
   # Or manually backup config, presets, sessions
   ```

2. **Pull new version**
   ```bash
   docker pull soundlab/phi-matrix:0.9.1
   ```

3. **Update docker-compose**
   ```yaml
   image: soundlab/phi-matrix:0.9.1
   ```

4. **Deploy update**
   ```bash
   docker-compose up -d
   ```

5. **Run smoke tests**
   ```bash
   python smoke/smoke_health.py
   ```

6. **Monitor for issues**
   ```bash
   docker logs -f soundlab-phi-matrix
   ```

### Rollback Procedure

See [RUNBOOK.md](RUNBOOK.md) for detailed rollback procedures.

Quick rollback:
```bash
make rollback
# Or manually:
docker-compose down
docker tag soundlab/phi-matrix:previous soundlab/phi-matrix:latest
docker-compose up -d
```

## Security Operations

### TLS/SSL Certificates

#### Let's Encrypt with Certbot
```bash
certbot certonly --standalone -d soundlab.example.com
```

#### Update Certificate Paths
```yaml
# docker-compose.yml
volumes:
  - /etc/letsencrypt/live/soundlab.example.com:/etc/nginx/ssl:ro
```

### Access Control

#### Enable Authentication (Optional)
```bash
# Generate token
openssl rand -hex 32

# Set in environment
export SOUNDLAB_AUTH_TOKEN=<generated_token>
```

#### Rate Limiting

Configure in NGINX:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20;
```

### Audit Logs

```bash
# Enable audit logging
export SOUNDLAB_AUDIT_LOG=true

# View audit events
tail -f logs/audit.log
```

## Disaster Recovery

### Backup Strategy

**Critical Data:**
- Configuration files (`server/config/`)
- Preset files (`server/presets/`)
- Session recordings (`server/sessions/`)

**Backup Schedule:**
- Real-time: Session recordings
- Daily: Configurations
- Weekly: Full system backup

**Backup Storage:**
- Local: `/backups/`
- Remote: S3, GCS, or equivalent

### Recovery Procedure

1. **Stop current instance**
2. **Restore from backup**
3. **Verify configuration**
4. **Start service**
5. **Run smoke tests**
6. **Monitor for 24 hours**

See [RUNBOOK.md](RUNBOOK.md) for detailed procedures.

## Support

### Gathering Diagnostic Information

```bash
# System information
uname -a
docker version
python --version

# Service logs
docker logs soundlab-phi-matrix > diagnostic-logs.txt

# Performance metrics
curl http://localhost:8000/metrics > diagnostic-metrics.txt

# Configuration
cat server/config/performance_profile.json > diagnostic-config.txt

# Package versions
pip list > diagnostic-packages.txt
```

### Creating Support Ticket

Include:
1. Version information (`/version`)
2. Error logs
3. Steps to reproduce
4. Expected vs actual behavior
5. System information

## References

- [INSTALLATION.md](INSTALLATION.md) - Installation procedures
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [RUNBOOK.md](RUNBOOK.md) - Deployment and emergency procedures
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
