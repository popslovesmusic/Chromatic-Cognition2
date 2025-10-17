# Soundlab Φ-Matrix - Operations Runbook

## Deployment Procedures

### Pre-Deployment Checklist

- [ ] Release candidate built and tested (`make rc`)
- [ ] All tests passing (`make test`)
- [ ] All validations passing (`make validate`)
- [ ] Security scans complete (`make security-scan`)
- [ ] SBOM generated (`make sbom`)
- [ ] Performance benchmarks meet targets
- [ ] Documentation updated
- [ ] Backup of current production
- [ ] Rollback plan reviewed
- [ ] Team notified of deployment window

### Production Deployment

#### Step 1: Preparation (T-30 minutes)

```bash
# 1. Backup current production
ssh production-host
cd /opt/soundlab
tar -czf backup-pre-deploy-$(date +%Y%m%d-%H%M%S).tar.gz \
  server/config/ \
  server/presets/ \
  server/sessions/

# 2. Move backup to safe location
mv backup-*.tar.gz /backups/

# 3. Verify backup
tar -tzf /backups/backup-pre-deploy-*.tar.gz | head

# 4. Tag previous version for rollback
docker tag soundlab/phi-matrix:latest soundlab/phi-matrix:previous
```

#### Step 2: Pull New Version (T-15 minutes)

```bash
# Pull new Docker image
docker pull soundlab/phi-matrix:0.9.0-rc1

# Verify image
docker inspect soundlab/phi-matrix:0.9.0-rc1 | jq '.[0].Config.Labels'

# Tag as latest
docker tag soundlab/phi-matrix:0.9.0-rc1 soundlab/phi-matrix:latest
```

#### Step 3: Deploy (T-5 minutes)

```bash
# Update docker-compose.yml
nano docker-compose.yml
# Change image: soundlab/phi-matrix:0.9.0-rc1

# Deploy new version
docker-compose down
docker-compose up -d

# Wait for startup
sleep 30
```

#### Step 4: Verification (T+0)

```bash
# 1. Health check
curl http://localhost:8000/healthz || echo "HEALTH CHECK FAILED"

# 2. Readiness check
curl http://localhost:8000/readyz || echo "READINESS CHECK FAILED"

# 3. Version verification
curl http://localhost:8000/version | jq '.version'

# 4. Smoke tests
cd /opt/soundlab
python smoke/smoke_health.py
python smoke/smoke_websocket.py

# 5. Monitor logs
docker logs -f soundlab-phi-matrix &
LOG_PID=$!
```

#### Step 5: Monitoring (T+5 to T+30 minutes)

```bash
# Watch metrics
watch -n 5 'curl -s http://localhost:8000/metrics | grep -E "cpu|memory|clients|latency"'

# Check for errors
docker logs soundlab-phi-matrix | grep -i error

# Monitor client connections
curl http://localhost:8000/api/status | jq '.metrics_clients'

# Test user flows
# - Open dashboard in browser
# - Connect to metrics stream
# - Load preset
# - Start Φ modulation
# - Verify visual rendering
```

#### Step 6: Go/No-Go Decision (T+30)

**GO Criteria:**
- ✅ Health checks passing
- ✅ No critical errors in logs
- ✅ Smoke tests passed
- ✅ Client connections working
- ✅ Metrics streaming at >=25 Hz
- ✅ WebSocket latency <100ms
- ✅ FPS >= 30

**NO-GO Criteria:**
- ❌ Health check failing
- ❌ Critical errors in logs
- ❌ Smoke tests failing
- ❌ Client connection issues
- ❌ Metrics not streaming
- ❌ High latency (>100ms)
- ❌ Low FPS (<30)

**If NO-GO:** Proceed to Rollback Procedure

#### Step 7: Post-Deployment (T+1 hour)

```bash
# 1. Stop monitoring log tail
kill $LOG_PID

# 2. Verify sustained performance
curl http://localhost:8000/api/dashboard/sync-health

# 3. Run extended smoke test
cd server
python validate_feature_017.py

# 4. Document deployment
echo "Deployment $(date): v0.9.0-rc1 successful" >> /var/log/soundlab-deployments.log

# 5. Notify team
# Send deployment completion notification
```

### Staging Deployment

```bash
# Use Makefile
make deploy-staging

# Or manually
docker-compose -f docker-compose.staging.yml up -d
sleep 30
make smoke-staging
```

## Rollback Procedures

### Quick Rollback (< 2 minutes)

#### Emergency Rollback

```bash
# 1. Stop current version
docker-compose down

# 2. Restore previous version
docker tag soundlab/phi-matrix:previous soundlab/phi-matrix:latest

# 3. Start previous version
docker-compose up -d

# 4. Wait for startup
sleep 30

# 5. Verify
curl http://localhost:8000/healthz
curl http://localhost:8000/version

# 6. Monitor
docker logs -f soundlab-phi-matrix
```

**Expected rollback time: ~90 seconds**

#### Makefile Rollback

```bash
make rollback
```

### Data Restoration

#### Restore Configuration

```bash
# 1. Stop service
docker-compose down

# 2. Restore from backup
tar -xzf /backups/backup-pre-deploy-20251017-100000.tar.gz

# 3. Copy restored files
cp -r server/config/ /opt/soundlab/server/
cp -r server/presets/ /opt/soundlab/server/

# 4. Set permissions
chown -R soundlab:soundlab /opt/soundlab/server/config/
chown -R soundlab:soundlab /opt/soundlab/server/presets/

# 5. Restart service
docker-compose up -d

# 6. Verify
python smoke/smoke_health.py
```

#### Restore Session Data

```bash
# 1. Locate backup
ls -lh /backups/backup-sessions-*.tar.gz

# 2. Extract
tar -xzf /backups/backup-sessions-20251017.tar.gz

# 3. Restore
cp -r server/sessions/* /opt/soundlab/server/sessions/

# 4. Verify
curl http://localhost:8000/api/recorder/sessions
```

## Emergency Procedures

### Service Outage

#### Detection
- Health checks failing
- No response from endpoints
- Container exited

#### Response (CRITICAL - Act within 5 minutes)

```bash
# 1. Check container status
docker ps -a | grep soundlab

# 2. View logs
docker logs --tail 100 soundlab-phi-matrix

# 3. Attempt restart
docker-compose restart soundlab

# 4. If restart fails, rollback
make rollback

# 5. If rollback fails, restore from backup
# See Data Restoration section

# 6. Notify team immediately
# Use incident management system
```

### Memory Leak / OOM

#### Detection
- High memory usage (>90%)
- OOM kills in logs
- Container restarts

#### Response

```bash
# 1. Check memory usage
docker stats soundlab-phi-matrix

# 2. Identify leak source
docker logs soundlab-phi-matrix | grep -i "memory\|oom"

# 3. Immediate mitigation - restart
docker-compose restart soundlab

# 4. Monitor
watch -n 5 'docker stats --no-stream soundlab-phi-matrix'

# 5. If leak persists, rollback
make rollback

# 6. Collect diagnostic data
docker logs soundlab-phi-matrix > oom-diagnostic-$(date +%Y%m%d-%H%M%S).log
```

### WebSocket Storm (Too Many Connections)

#### Detection
- High CPU usage
- WebSocket client count abnormally high
- Connection timeouts

#### Response

```bash
# 1. Check client count
curl http://localhost:8000/metrics | grep websocket_clients

# 2. Apply rate limiting (if not already)
# Update nginx.conf:
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn addr 10;

# 3. Restart nginx
docker-compose restart nginx

# 4. Monitor connections
watch -n 2 'curl -s http://localhost:8000/metrics | grep websocket_clients'

# 5. If still overwhelmed, enable connection limits in app
export SOUNDLAB_MAX_CONNECTIONS=50
docker-compose restart soundlab
```

### Database Corruption (If Applicable)

#### Detection
- Errors reading/writing sessions
- Data inconsistencies

#### Response

```bash
# 1. Stop service
docker-compose down

# 2. Backup corrupted data
mv server/sessions server/sessions.corrupted

# 3. Restore from backup
tar -xzf /backups/backup-sessions-latest.tar.gz

# 4. Restart service
docker-compose up -d

# 5. Verify
curl http://localhost:8000/api/recorder/sessions
```

## Routine Operations

### Daily Operations

```bash
# Morning checklist
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
docker logs --since 24h soundlab-phi-matrix | grep -i error
curl http://localhost:8000/metrics | grep -E "cpu|memory|clients"

# Evening checklist
# Review day's logs
# Check disk space
# Verify backup completed
```

### Weekly Operations

```bash
# Performance review
cd /opt/soundlab/server
python benchmark_runner.py > weekly-benchmark-$(date +%Y%m%d).txt

# Backup verification
ls -lh /backups/ | tail -7

# Update check
docker pull soundlab/phi-matrix:latest
docker inspect soundlab/phi-matrix:latest | jq '.[0].Config.Labels'
```

### Monthly Operations

```bash
# Security updates
docker pull soundlab/phi-matrix:latest

# Clean old backups (keep 30 days)
find /backups/ -name "backup-*.tar.gz" -mtime +30 -delete

# Full benchmark
make validate

# Review and archive old sessions
cd /opt/soundlab/server
python archive_sessions.py --days 90
```

## Disaster Recovery

### Complete System Failure

#### Recovery Steps

1. **Provision new host**
2. **Install Docker**
3. **Clone repository**
   ```bash
   git clone https://github.com/soundlab/phi-matrix.git
   cd phi-matrix
   git checkout v0.9.0-rc1
   ```

4. **Restore backups**
   ```bash
   scp backup-host:/backups/backup-latest.tar.gz .
   tar -xzf backup-latest.tar.gz
   ```

5. **Deploy**
   ```bash
   make deploy-staging
   ```

6. **Verify**
   ```bash
   make smoke
   ```

7. **Switch DNS/Load Balancer**

**Recovery Time Objective (RTO):** 30 minutes
**Recovery Point Objective (RPO):** 1 hour (last backup)

## Contacts

### On-Call Rotation

| Day | Primary | Secondary |
|-----|---------|-----------|
| Mon-Wed | Engineer A | Engineer B |
| Thu-Sat | Engineer B | Engineer C |
| Sun | Engineer C | Engineer A |

### Escalation Path

1. **L1:** On-call engineer (respond within 15 min)
2. **L2:** Senior engineer (30 min)
3. **L3:** Tech lead (1 hour)
4. **L4:** CTO (2 hours)

### External Services

- **Cloud Provider:** [Contact info]
- **CDN Provider:** [Contact info]
- **Monitoring:** [Grafana/Prometheus]

## Change Log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2025-10-17 | 0.9.0-rc1 | Initial RC | Team |

## Review Schedule

- Review this runbook: Monthly
- Test rollback procedure: Quarterly
- Test DR procedure: Annually
