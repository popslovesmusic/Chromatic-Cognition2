# Incident Response Playbook - Feature 024

**Soundlab Φ-Matrix Security Incident Response**

## Overview

This playbook defines procedures for detecting, triaging, containing, eradicating, and reviewing security incidents.

**Incident Response Phases:**
1. **Detect** - Identify potential security incident
2. **Triage** - Assess severity and impact
3. **Contain** - Limit damage and prevent spread
4. **Eradicate** - Remove threat and restore systems
5. **Review** - Post-incident analysis and improvements

## Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| **P0 - Critical** | Active breach, data loss, system compromise | Immediate (< 15 min) | Database breach, active RCE exploit |
| **P1 - High** | Potential breach, severe vulnerability | < 1 hour | Unpatched critical CVE, auth bypass |
| **P2 - Medium** | Security weakness, degraded security | < 4 hours | Rate limit bypass, minor data leak |
| **P3 - Low** | Security concern, no immediate risk | < 24 hours | Config drift, outdated dependency |

## Incident Types

### Type 1: Authentication/Authorization Breach
- Compromised JWT keys
- Unauthorized access
- Token theft/replay

### Type 2: Data Breach
- PII exposure
- Log file leak
- Database compromise

### Type 3: Denial of Service
- DDoS attack
- Resource exhaustion
- Service disruption

### Type 4: Code Injection
- XSS attack
- SQL injection
- Remote code execution

### Type 5: Supply Chain Attack
- Compromised dependency
- Malicious package
- Build system compromise

## Phase 1: Detect

### Detection Sources

1. **Automated Monitoring**
   - Security event logs
   - Rate limit violations
   - Failed authentication attempts
   - Anomaly detection alerts

2. **Manual Reports**
   - User reports
   - Security researcher disclosure
   - Internal security audit

3. **External Notifications**
   - CVE databases
   - Dependency vulnerability alerts
   - Threat intelligence feeds

### Detection Checklist

```bash
# Check recent security events
tail -n 100 logs/security.log | grep -E "(CRITICAL|ERROR|WARN)"

# Check authentication failures
grep "auth_failed" logs/audit.log | tail -n 50

# Check rate limit violations
grep "rate_limit_exceeded" logs/security.log | tail -n 20

# Check WebSocket anomalies
grep "websocket.*error" logs/server.log | tail -n 20

# Check for suspicious IPs
awk '{print $1}' logs/access.log | sort | uniq -c | sort -rn | head -n 10
```

## Phase 2: Triage

### Triage Questions

1. **What happened?**
   - What system/component is affected?
   - What type of incident is this?
   - When did it start?

2. **What's the impact?**
   - How many users affected?
   - What data is at risk?
   - Is the attack ongoing?

3. **What's the severity?**
   - P0/P1/P2/P3 classification
   - Business impact assessment
   - Required response time

### Triage Procedure

```bash
# 1. Gather initial evidence
mkdir -p incident_$(date +%Y%m%d_%H%M%S)
cd incident_*

# 2. Capture system state
cp /var/log/soundlab/* ./logs/
docker logs soundlab-api > docker-api.log 2>&1
netstat -tulpn > network-state.txt
ps aux > process-state.txt

# 3. Capture application state
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/security/stats > security-stats.json

# 4. Document timeline
echo "$(date -Iseconds) - Incident detected" > timeline.txt
```

### Severity Assessment Matrix

| Impact | Confidentiality | Integrity | Availability | → Severity |
|--------|----------------|-----------|--------------|------------|
| High | Data breach | Data tampering | Total outage | P0 |
| Medium | Limited leak | Config change | Partial outage | P1 |
| Low | Log exposure | Cosmetic change | Degraded perf | P2 |
| Minimal | No disclosure | No change | No impact | P3 |

## Phase 3: Contain

### Containment Strategies

#### Immediate Actions (P0/P1)

1. **Isolate Affected Systems**
   ```bash
   # Stop affected service
   docker-compose stop soundlab-api

   # Block malicious IPs at firewall
   sudo iptables -A INPUT -s <ATTACKER_IP> -j DROP

   # Disable compromised accounts
   python scripts/admin.py disable-user --user-id <USER_ID>
   ```

2. **Rotate Credentials**
   ```bash
   # Rotate JWT keys
   python scripts/rotate_keys.py --emergency

   # Invalidate all active tokens
   python scripts/admin.py revoke-all-tokens

   # Rotate API keys
   python scripts/rotate_api_keys.py
   ```

3. **Enable Enhanced Monitoring**
   ```bash
   # Increase log verbosity
   export LOG_LEVEL=DEBUG

   # Enable security event streaming
   python scripts/monitor.py --mode=security --stream
   ```

#### Containment Playbooks

**Playbook C-001: Compromised JWT Key**
```bash
# 1. Generate new key pair
openssl genrsa -out config/keys/jwt_private_new.pem 4096
openssl rsa -in config/keys/jwt_private_new.pem \
  -pubout -out config/keys/jwt_public_new.pem

# 2. Update configuration
sed -i 's/jwt_private.pem/jwt_private_new.pem/' config/security.yaml

# 3. Restart service with new keys
docker-compose restart soundlab-api

# 4. Force logout all users
python scripts/admin.py force-logout-all

# 5. Notify users to re-authenticate
python scripts/notify.py --template key-rotation --all-users
```

**Playbook C-002: Active Data Breach**
```bash
# 1. Immediately take API offline
docker-compose stop soundlab-api

# 2. Capture forensic evidence
tar czf evidence_$(date +%Y%m%d).tar.gz \
  logs/ config/ /var/lib/docker/volumes/

# 3. Block all external access
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP
sudo iptables -A INPUT -p tcp --dport 443 -j DROP

# 4. Analyze breach scope
python scripts/breach_analysis.py \
  --logs logs/ --output breach-report.json

# 5. Notify affected users (if PII involved)
python scripts/breach_notification.py \
  --affected breach-report.json
```

**Playbook C-003: DDoS Attack**
```bash
# 1. Enable aggressive rate limiting
export RATE_LIMIT_REST=10  # requests/10s
export RATE_LIMIT_WS_HANDSHAKE=2

# 2. Restart with DDoS protection
docker-compose restart soundlab-api

# 3. Enable CDN/WAF DDoS protection
# (specific to your CDN provider)

# 4. Block attack source IPs
cat attack-ips.txt | while read ip; do
  sudo iptables -A INPUT -s $ip -j DROP
done

# 5. Monitor attack mitigation
watch -n 5 'grep "rate_limit" logs/security.log | tail -n 20'
```

## Phase 4: Eradicate

### Eradication Checklist

- [ ] Root cause identified
- [ ] Vulnerability patched
- [ ] Malicious code removed
- [ ] Compromised credentials rotated
- [ ] Systems hardened
- [ ] Clean backup restored (if needed)

### Eradication Procedures

#### Patch Vulnerability

```bash
# 1. Identify vulnerable component
# (from triage analysis)

# 2. Apply security patch
pip install --upgrade <vulnerable-package>

# or for system packages
apt-get update && apt-get upgrade <package>

# 3. Rebuild and test
docker-compose build --no-cache
docker-compose up -d
make security-scan  # Verify fix
```

#### Remove Malicious Code

```bash
# 1. Identify malicious files
find . -type f -newermt "<incident-time>" ! -path "./.git/*"

# 2. Restore from clean backup
git checkout <last-known-good-commit> -- <file>

# or restore from backup
tar xzf backups/clean-backup.tar.gz

# 3. Verify integrity
sha256sum -c checksums.txt
```

#### Harden Systems

```bash
# 1. Apply security updates
python scripts/apply_security_updates.py

# 2. Tighten firewall rules
python scripts/firewall_rules.py --mode strict

# 3. Enable additional security controls
export ENABLE_MFA=true
export ENABLE_IP_ALLOWLIST=true

# 4. Restart with hardened config
docker-compose -f docker-compose.yml \
  -f docker-compose.security.yml up -d
```

## Phase 5: Review

### Post-Incident Review (PIR)

**Timeline: Within 72 hours of incident resolution**

#### PIR Agenda

1. **Incident Summary** (15 min)
   - What happened?
   - Timeline of events
   - Impact assessment

2. **Response Analysis** (20 min)
   - What went well?
   - What could be improved?
   - Response time metrics

3. **Root Cause Analysis** (20 min)
   - Why did this happen?
   - What were contributing factors?
   - How was it not caught earlier?

4. **Action Items** (15 min)
   - Immediate fixes
   - Process improvements
   - Preventive measures

5. **Documentation** (10 min)
   - Update playbooks
   - Share learnings
   - Update threat model

#### PIR Template

```markdown
# Post-Incident Review: [Incident ID]

**Date**: [Date]
**Severity**: [P0/P1/P2/P3]
**Duration**: [Total time to resolution]
**Attendees**: [Names]

## Executive Summary
[2-3 sentence summary]

## Timeline
| Time | Event | Actor |
|------|-------|-------|
| T+0 | Incident detected | Monitoring system |
| T+15m | Containment initiated | On-call engineer |
| ... | ... | ... |

## Impact
- Users affected: [Number]
- Data affected: [Description]
- Downtime: [Duration]
- Financial impact: [Estimate]

## Root Cause
[Detailed root cause analysis]

## Response Effectiveness
**What went well:**
- [Item 1]
- [Item 2]

**What could be improved:**
- [Item 1]
- [Item 2]

## Action Items
| Action | Owner | Deadline | Status |
|--------|-------|----------|--------|
| [Action 1] | [Name] | [Date] | [ ] |
| [Action 2] | [Name] | [Date] | [ ] |

## Preventive Measures
- [Measure 1]
- [Measure 2]

## Documentation Updates
- [ ] Update incident response playbook
- [ ] Update threat model
- [ ] Update security training
```

### Lessons Learned Database

Store PIRs in `docs/incidents/` for future reference:

```bash
docs/incidents/
├── 2025-01-15_jwt-key-compromise.md
├── 2025-02-03_ddos-attack.md
└── 2025-03-12_dependency-vuln.md
```

## Communication Templates

### Internal Communication (Slack/Email)

```
🚨 SECURITY INCIDENT - [Severity]

Type: [Incident type]
Status: [Detected/Containing/Resolved]
Impact: [Brief description]

Current Actions:
- [Action 1]
- [Action 2]

Next Update: [Time]

War Room: [Link to incident channel]
```

### User Communication (Breach Notification)

```
Subject: Important Security Notice - Action Required

Dear [User],

We are writing to inform you of a security incident that may have
affected your account.

What Happened:
[Brief, non-technical description]

What Information Was Involved:
[Specific data types]

What We're Doing:
- [Action 1]
- [Action 2]

What You Should Do:
1. [User action 1]
2. [User action 2]

We take security seriously and are working to prevent this from
happening again.

Contact: security@soundlab.example.com

Sincerely,
[Name]
[Title]
```

## Tools and Resources

### Security Tools

```bash
# Log analysis
grep -r "CRITICAL\|ERROR" logs/

# Network analysis
tcpdump -i any -w capture.pcap port 8000

# File integrity check
tripwire --check

# Forensic imaging
dd if=/dev/sda of=disk-image.dd bs=4M
```

### Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| On-call Engineer | on-call@soundlab.com | Immediate |
| Security Lead | security@soundlab.com | P0/P1 |
| Infrastructure Lead | infra@soundlab.com | P0/P1 |
| Executive Team | exec@soundlab.com | P0 only |
| Legal | legal@soundlab.com | Data breach |
| PR/Comms | pr@soundlab.com | Public incident |

### External Resources

- NIST Incident Response: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf
- SANS Incident Handling: https://www.sans.org/reading-room/whitepapers/incident/incident-handlers-handbook-33901
- CVE Database: https://cve.mitre.org/

## Appendix: Quick Reference

### Emergency Commands

```bash
# Kill all active sessions
python scripts/admin.py kill-all-sessions

# Rotate all credentials
./scripts/emergency_rotation.sh

# Take system offline
docker-compose down && sudo iptables -A INPUT -j DROP

# Restore from backup
./scripts/restore_backup.sh --date <YYYY-MM-DD>

# Enable maintenance mode
touch .maintenance && docker-compose restart
```

### Evidence Collection

```bash
# Create evidence bundle
tar czf evidence_$(date +%Y%m%d_%H%M%S).tar.gz \
  logs/ \
  config/ \
  /var/lib/docker/ \
  /etc/nginx/ \
  /etc/ssl/

# Calculate hashes for legal chain of custody
sha256sum evidence_*.tar.gz > evidence_hashes.txt
gpg --sign evidence_hashes.txt
```
