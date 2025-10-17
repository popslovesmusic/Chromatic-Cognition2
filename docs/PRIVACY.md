# Privacy Policy

**Soundlab Φ-Matrix Privacy Policy**

*Last Updated: 2025-10-17*

## Overview

This privacy policy describes how Soundlab Φ-Matrix ("we", "our", "the system") collects, uses, stores, and protects your data. We are committed to data minimization, transparency, and user privacy.

## Data We Collect

### 1. Essential Data (Always Collected)

**Session Metadata**
- Session timestamps
- Session duration
- Feature usage statistics
- Performance metrics

**Purpose**: System operation, performance monitoring, debugging

**Retention**: 90 days

### 2. Optional Data (Collected with Consent)

**Audio Processing Data**
- Phi-depth, phi-phase, coherence values
- Real-time consciousness metrics
- Processed audio characteristics (no raw audio stored)

**Purpose**: Algorithm improvement, research

**Retention**: 30 days

**User Presets**
- Preset names and configurations
- UI preferences
- Layout settings

**Purpose**: Personalization, user experience

**Retention**: 365 days or until user deletion

### 3. Technical Data

**System Logs**
- API access logs (IP addresses redacted)
- Error logs (PII redacted)
- Performance logs

**Purpose**: Security monitoring, debugging, system health

**Retention**: 30 days (90 days for session metrics)

**Security Audit Logs**
- Authentication attempts
- Admin actions
- Data access/export/deletion events

**Purpose**: Security compliance, incident response

**Retention**: 365 days

## Data We DO NOT Collect

We explicitly **do not** collect:
- ❌ Raw audio recordings (unless explicitly saved by user)
- ❌ Personally identifiable information (PII) beyond what's required for authentication
- ❌ Third-party tracking cookies
- ❌ Browser fingerprinting data
- ❌ Keystroke logging or screen recording
- ❌ Location data beyond IP geolocation for security

## How We Use Your Data

### Primary Uses

1. **System Operation**
   - Process audio in real-time
   - Generate consciousness metrics
   - Maintain user sessions

2. **Performance Optimization**
   - Monitor system health
   - Identify bottlenecks
   - Improve algorithms

3. **Security & Safety**
   - Detect and prevent abuse
   - Monitor for security threats
   - Audit admin actions

### Data Sharing

**We do not sell or share your data with third parties.**

Limited data may be shared in these cases:
- **Legal Requirements**: If required by law or valid legal process
- **Security Incidents**: With security researchers for responsible disclosure
- **Service Providers**: With vetted providers under strict data processing agreements

## Data Protection Measures

### Security Controls

**In Transit**
- TLS 1.2+ encryption for all connections
- HTTPS enforcement with HSTS
- Secure WebSocket connections (WSS)

**At Rest**
- AES-256-GCM encryption for sensitive data
- Encrypted database storage
- Secure key management with rotation

**Access Control**
- JWT token authentication
- Role-based access control (RBAC)
- Audit logging for all data access

### Privacy by Design

**Data Minimization**
- Collect only what's necessary
- Automatic data purging per retention policy
- No raw audio in logs

**PII Redaction**
- Automated PII detection and redaction
- Email addresses anonymized in logs
- IP addresses partially masked

**Frontend Storage**
- No tokens or secrets in localStorage
- Preset names only (no sensitive data)
- Session storage for temporary data

## Your Rights

You have the right to:

### 1. Access Your Data
Request a copy of all data we hold about you.

**How**: Contact security@soundlab.example.com with subject "Data Access Request"

**Timeline**: We will respond within 30 days

### 2. Correct Your Data
Request corrections to inaccurate data.

**How**: Update via dashboard settings or contact support

### 3. Delete Your Data
Request deletion of your account and associated data.

**How**:
```bash
# Self-service deletion (if enabled)
Dashboard → Settings → Delete Account

# Or contact us
Email: privacy@soundlab.example.com
```

**What gets deleted**:
- User presets
- Session history
- Stored metrics
- Account credentials

**What we retain** (anonymized):
- Aggregated analytics
- Security logs (365 days)
- Crash reports (90 days)

### 4. Export Your Data
Download your data in machine-readable format.

**How**: Dashboard → Settings → Export Data

**Format**: JSON or CSV

**Includes**:
- All user presets
- Session statistics
- Configuration history

### 5. Opt-Out of Analytics
Disable optional data collection.

**How**: Dashboard → Settings → Privacy → Disable Analytics

## Data Retention Policy

| Data Type | Retention Period | Auto-Purge |
|-----------|------------------|------------|
| Session Metrics | 90 days | ✓ |
| System Logs | 30 days | ✓ |
| Audit Logs | 365 days | ✓ |
| User Presets | 365 days or until deletion | ✓ |
| Crash Reports | 90 days | ✓ |
| Temp Files | 7 days | ✓ |
| Recordings (if saved) | 30 days or until deletion | ✓ |

**Automated Purge**: Runs daily at 02:00 UTC

**Manual Purge**:
```bash
python scripts/purge_retention.py --dry-run  # Preview
python scripts/purge_retention.py            # Execute
```

## Cookies and Local Storage

### Cookies We Use

**Essential Cookies** (Required)
- `session_id`: User session management (15 minutes)
- `csrf_token`: CSRF protection (session lifetime)

**Functional Cookies** (Optional)
- `ui_theme`: Dark/light mode preference
- `layout_config`: Dashboard layout

**Security Cookies**
- `SameSite=Strict` for all cookies
- `Secure` flag (HTTPS only)
- `HttpOnly` for session cookies

### Local Storage

We use localStorage only for:
- Preset names (no sensitive data)
- UI preferences
- Theme settings

**Never stored in localStorage:**
- Authentication tokens
- Passwords or secrets
- API keys
- Session data

## Children's Privacy

Soundlab is not directed at children under 13. We do not knowingly collect data from children under 13. If you believe we have collected such data, contact us immediately at privacy@soundlab.example.com.

## International Data Transfers

If you access Soundlab from outside [Your Region], your data may be transferred to and processed in [Region]. We ensure adequate protections for international transfers through:
- Standard Contractual Clauses (SCCs)
- Encryption in transit and at rest
- Equivalent security standards

## Changes to This Policy

We may update this privacy policy. When we do:

1. **Notification**: Users will be notified via dashboard banner
2. **Effective Date**: Changes take effect 30 days after notification
3. **Version History**: All versions available at `/docs/privacy-history/`

**How to stay informed**: Check this page periodically or subscribe to policy updates

## Contact Us

### Privacy Inquiries
- **Email**: privacy@soundlab.example.com
- **Response Time**: Within 7 business days

### Data Protection Officer (DPO)
- **Email**: dpo@soundlab.example.com
- **Address**: [Your Address]

### Security Concerns
- **Email**: security@soundlab.example.com
- **PGP Key**: [Key ID] (available at /security.txt)

### General Support
- **GitHub Issues**: https://github.com/soundlab/phi-matrix/issues
- **Documentation**: https://docs.soundlab.example.com

## Legal Basis (GDPR)

If you are in the EU/EEA, our legal bases for processing are:

- **Contract Performance**: Processing necessary for service delivery
- **Legitimate Interest**: Security monitoring, system optimization
- **Consent**: Optional analytics, marketing (if applicable)
- **Legal Obligation**: Compliance with laws, legal requests

You may withdraw consent at any time without affecting service quality.

## Compliance Frameworks

Soundlab privacy practices align with:

- **GDPR** (General Data Protection Regulation)
- **CCPA** (California Consumer Privacy Act)
- **PIPEDA** (Personal Information Protection and Electronic Documents Act)

## Transparency Report

We publish a quarterly transparency report including:
- Data requests received (law enforcement, legal)
- Data breaches (if any)
- Security incidents
- Privacy policy changes

**Latest Report**: [Link to transparency reports]

## Automated Decision Making

We do not use automated decision-making or profiling that produces legal effects or significantly affects users.

Algorithmic processing (audio → Φ metrics) is:
- Purely computational
- No user profiling
- No behavioral predictions
- User-controlled

## Data Breach Notification

In the event of a data breach affecting your personal data:

1. **Notification Timeline**: Within 72 hours of discovery
2. **Notification Method**: Email to registered address
3. **Information Provided**:
   - What data was affected
   - What we're doing about it
   - What you should do
   - How to contact us

**See Also**: [Incident Response Playbook](incident_response.md)

## Your California Privacy Rights (CCPA)

If you are a California resident, you have additional rights:

- **Right to Know**: What data we collect and how we use it
- **Right to Delete**: Request deletion of your data
- **Right to Opt-Out**: Opt-out of data "sale" (we don't sell data)
- **Right to Non-Discrimination**: Equal service regardless of privacy choices

**Exercise your rights**: privacy@soundlab.example.com

## Acknowledgment

By using Soundlab, you acknowledge that you have read and understood this Privacy Policy.

---

**Version**: 1.0
**Effective Date**: 2025-10-17
**Next Review**: 2026-01-17
