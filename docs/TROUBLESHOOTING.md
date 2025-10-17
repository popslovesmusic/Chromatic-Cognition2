# Soundlab Φ-Matrix - Troubleshooting Guide

## Common Issues

### Server Won't Start

#### Symptom
Container exits immediately or server fails to bind to port

#### Causes & Solutions

**Port already in use:**
```bash
# Check what's using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Solution 1: Kill the process
kill -9 <PID>

# Solution 2: Use different port
docker run -p 8001:8000 soundlab/phi-matrix:0.9.0-rc1
```

**Permission denied:**
```bash
# Run as current user
docker run --user $(id -u):$(id -g) ...

# Or fix permissions
sudo chown -R $USER:$USER logs/ server/config/
```

**Missing dependencies:**
```bash
# Reinstall dependencies
pip install --force-reinstall -r server/requirements.txt
```

### WebSocket Connection Issues

#### Symptom
Dashboard shows "DISCONNECTED" or WebSocket errors in console

#### Diagnosis
```bash
# Test WebSocket connectivity
python smoke/smoke_websocket.py

# Check server logs
docker logs soundlab-phi-matrix | grep -i websocket

# Verify endpoint
curl http://localhost:8000/healthz
```

#### Solutions

**CORS issues:**
```bash
# Enable CORS
export SOUNDLAB_ENABLE_CORS=true

# Or in docker-compose.yml
environment:
  - SOUNDLAB_ENABLE_CORS=true
```

**Reverse proxy misconfiguration:**
```nginx
# In nginx.conf, ensure WebSocket upgrade:
location /ws/ {
    proxy_pass http://soundlab:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

**Network timeout:**
```bash
# Increase timeout
docker run -e SOUNDLAB_WEBSOCKET_TIMEOUT=30 ...
```

### High Latency / Low FPS

#### Symptom
Dashboard shows FPS < 30 or latency > 100ms

#### Diagnosis
```bash
# Check current performance
curl http://localhost:8000/metrics | grep -E "fps|latency|cpu"

# Run benchmark
cd server && python benchmark_runner.py

# Check adaptive scaling
curl http://localhost:8000/api/dashboard/sync-health
```

#### Solutions

**CPU overload:**
```bash
# Check CPU usage
curl http://localhost:8000/metrics | grep cpu_percent

# Reduce visual complexity
# Edit server/config/performance_profile.json:
{
  "visual_complexity_level": 3,  # Reduce from 5
  "target_fps": 30  # Reduce from 45/60
}

# Restart
docker-compose restart soundlab
```

**Memory pressure:**
```bash
# Check memory
docker stats soundlab-phi-matrix

# Increase memory limit
docker run -m 4g ...

# Or in docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 4G
```

**Network latency:**
```bash
# Test latency to server
ping localhost

# Run sync profiler
cd server && python sync_profiler.py

# Use local deployment (avoid remote)
```

### Audio Issues

#### Symptom
No audio output or audio glitches/dropouts

#### Diagnosis
```bash
# Check audio server status
curl http://localhost:8000/api/status | jq '.audio_running'

# List audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Check buffer size
curl http://localhost:8000/api/status | jq '.buffer_size'
```

#### Solutions

**Audio device not found:**
```python
# In server/main.py or via environment:
export SOUNDLAB_AUDIO_DEVICE_ID=1

# Or disable audio for testing:
export SOUNDLAB_AUDIO_ENABLED=false
```

**Buffer underruns:**
```bash
# Increase buffer size
# Edit server/config/performance_profile.json:
{
  "audio_buffer_ms": 20  # Increase from 10
}
```

**Sample rate mismatch:**
```bash
# Set correct sample rate
export SOUNDLAB_SAMPLE_RATE=48000
```

### Memory Leaks

#### Symptom
Memory usage grows over time, eventually causing OOM

#### Diagnosis
```bash
# Monitor memory over time
watch -n 5 'docker stats --no-stream soundlab-phi-matrix'

# Check for websocket leaks
curl http://localhost:8000/metrics | grep websocket_clients

# Run memory stability test
cd server && python validate_feature_018.py
```

#### Solutions

**Orphaned WebSocket connections:**
```bash
# Restart to clear
docker-compose restart soundlab

# Configure connection timeout
export SOUNDLAB_WEBSOCKET_TIMEOUT=60
```

**Session recorder not cleaning up:**
```bash
# Clean old sessions
rm -rf server/sessions/*.old

# Configure retention
# In config:
{
  "session_retention_days": 7
}
```

**Check for memory leaks in logs:**
```bash
docker logs soundlab-phi-matrix | grep -i "memory\|leak\|oom"
```

### Slow Dashboard Load

#### Symptom
Dashboard takes >5s to load or is unresponsive

#### Diagnosis
```bash
# Check server response time
time curl http://localhost:8000/healthz

# Check static file serving
time curl http://localhost:8000/static/phi-matrix-dashboard.html

# Check network
ping localhost
```

#### Solutions

**Enable compression:**
```nginx
# In nginx.conf
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

**Use CDN for static assets:**
```html
<!-- Use CDN for libraries -->
<script src="https://cdn.jsdelivr.net/npm/..."></script>
```

**Reduce initial complexity:**
```javascript
// In phi-matrix-dashboard.js, start at lower complexity
const initialComplexity = 3;  // Instead of 5
```

## Error Messages

### "Health check failed"

**Meaning:** Server not responding to health endpoint

**Solutions:**
```bash
# 1. Check if server is running
docker ps

# 2. Check logs
docker logs soundlab-phi-matrix

# 3. Restart
docker-compose restart soundlab

# 4. Verify health endpoint
curl -v http://localhost:8000/healthz
```

### "503 Service Unavailable"

**Meaning:** Server is running but not ready

**Solutions:**
```bash
# Check readiness
curl http://localhost:8000/readyz

# Check which component is not ready
curl http://localhost:8000/readyz | jq '.checks'

# Wait for initialization (may take 30-60s on first start)
sleep 60 && curl http://localhost:8000/readyz
```

### "WebSocket closed with code 1006"

**Meaning:** WebSocket connection abnormally closed

**Causes:**
- Server crashed
- Network interruption
- Timeout
- Resource exhaustion

**Solutions:**
```bash
# Check server logs
docker logs soundlab-phi-matrix | tail -50

# Enable reconnection in client
# (Already implemented in phi-matrix-dashboard.js)

# Increase timeout
export SOUNDLAB_WEBSOCKET_TIMEOUT=60
```

### "ModuleNotFoundError: No module named 'xyz'"

**Meaning:** Missing Python dependency

**Solutions:**
```bash
# Reinstall dependencies
pip install -r server/requirements.txt

# Or rebuild Docker image
docker-compose build --no-cache soundlab
```

## Performance Optimization

### Benchmark Below Targets

If benchmark shows:
- FPS < 30
- Latency > 50ms
- CPU > 60%
- Memory growth > 5%

**Step 1: Profile performance**
```bash
cd server
python benchmark_runner.py
```

**Step 2: Adjust settings**
```json
// server/config/performance_profile.json
{
  "target_fps": 30,
  "audio_buffer_ms": 15,
  "visual_complexity_level": 3,
  "enable_phi_breathing": true,
  "enable_topology_links": false,  // Disable expensive features
  "enable_gradients": true,
  "render_resolution": 0.8  // Reduce from 1.0
}
```

**Step 3: Test again**
```bash
python validate_feature_018.py
```

## Debugging

### Enable Debug Logging

```bash
# Set log level
export SOUNDLAB_LOG_LEVEL=debug

# Or in docker-compose.yml:
environment:
  - SOUNDLAB_LOG_LEVEL=debug
```

### Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use ipdb for better interface
import ipdb; ipdb.set_trace()
```

### Monitor Real-Time Metrics

```bash
# Watch metrics
watch -n 1 'curl -s http://localhost:8000/metrics | grep -E "cpu|memory|latency|fps"'

# Or use Prometheus + Grafana dashboard
```

### Network Debugging

```bash
# Capture WebSocket traffic
tcpdump -i any -A 'port 8000'

# Use browser dev tools
# - Open Network tab
# - Filter WS
# - Watch frames
```

## Getting Help

### Before Reporting an Issue

1. **Check this troubleshooting guide**
2. **Search existing issues**: https://github.com/soundlab/phi-matrix/issues
3. **Run diagnostics**:
   ```bash
   # Collect diagnostic info
   sh diagnostics.sh > diagnostics.txt
   ```

### Reporting a Bug

Include:
1. **Version** (`curl http://localhost:8000/version`)
2. **Environment** (OS, Docker version, hardware)
3. **Steps to reproduce**
4. **Expected vs actual behavior**
5. **Logs** (`docker logs soundlab-phi-matrix`)
6. **Configuration** (sanitized)
7. **Diagnostic output**

### Community Support

- GitHub Issues: https://github.com/soundlab/phi-matrix/issues
- Discussions: https://github.com/soundlab/phi-matrix/discussions
- Documentation: https://soundlab.github.io/phi-matrix/

## Emergency Procedures

### Service is Down

```bash
# 1. Check health
curl http://localhost:8000/healthz || echo "FAILED"

# 2. Check if container is running
docker ps | grep soundlab

# 3. View recent logs
docker logs --tail 100 soundlab-phi-matrix

# 4. Restart
docker-compose restart soundlab

# 5. If restart fails, rollback
make rollback

# 6. Verify
python smoke/smoke_health.py
```

### Data Loss Prevention

```bash
# Immediate backup
tar -czf emergency-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  server/config/ \
  server/presets/ \
  server/sessions/

# Move to safe location
mv emergency-backup-*.tar.gz /backups/
```

See [RUNBOOK.md](RUNBOOK.md) for full emergency procedures.
