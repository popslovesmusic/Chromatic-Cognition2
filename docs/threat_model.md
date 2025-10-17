# Threat Model - Feature 024

**Soundlab Φ-Matrix Security Analysis (STRIDE)**

## Overview

This threat model analyzes the Soundlab Φ-Matrix system using the STRIDE methodology to identify security threats, data flows, trust boundaries, and mitigations.

**STRIDE Categories:**
- **S**poofing Identity
- **T**ampering with Data
- **R**epudiation
- **I**nformation Disclosure
- **D**enial of Service
- **E**levation of Privilege

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└───────────────────────────┬─────────────────────────────────┘
                            │ TLS 1.2+
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Nginx/Caddy (Reverse Proxy)              │
│                  Trust Boundary: Internet → DMZ             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴────────────┐
                │                        │
                ▼                        ▼
┌──────────────────────┐       ┌─────────────────────┐
│  Static Frontend     │       │  FastAPI Backend    │
│  (React/Vue)         │       │  (Python)           │
│  Trust Boundary:     │       │  Trust Boundary:    │
│  Browser Sandbox     │       │  Application Logic  │
└──────────────────────┘       └──────────┬──────────┘
                                          │
                        ┌─────────────────┼─────────────────┐
                        │                 │                 │
                        ▼                 ▼                 ▼
                ┌────────────┐    ┌──────────┐    ┌─────────────┐
                │ File       │    │ Hardware │    │ Logs/       │
                │ Storage    │    │ Sensors  │    │ Audit Trail │
                └────────────┘    └──────────┘    └─────────────┘
```

### Data Flows

1. **User Authentication Flow**
   ```
   Browser → [HTTPS] → Nginx → [HTTP/WS] → FastAPI → [Verify JWT] → Grant Access
   ```

2. **Sensor Data Flow**
   ```
   Hardware → I²S Bridge → SensorManager → WebSocket → Browser Dashboard
   ```

3. **Configuration Flow**
   ```
   Admin → [Auth] → API → [Validate] → Write Config → [Audit Log]
   ```

## Trust Boundaries

### TB-1: Internet → Reverse Proxy
- **Boundary**: Public internet to DMZ
- **Controls**: TLS termination, rate limiting, DDoS protection
- **Threats**: Network attacks, TLS downgrade, DoS

### TB-2: Reverse Proxy → Application
- **Boundary**: DMZ to application layer
- **Controls**: Origin validation, header sanitization
- **Threats**: Request smuggling, header injection

### TB-3: Browser → Application
- **Boundary**: Client browser to backend
- **Controls**: CSP, CORS, token auth, CSRF protection
- **Threats**: XSS, CSRF, token theft

### TB-4: Application → Storage
- **Boundary**: Application logic to persistent storage
- **Controls**: Encryption at rest, access controls
- **Threats**: SQL injection, path traversal, data tampering

### TB-5: Application → Hardware
- **Boundary**: Software to hardware sensors
- **Controls**: Command validation, rate limiting
- **Threats**: Buffer overflow, hardware exploitation

## Threats (STRIDE Analysis)

### S - Spoofing Identity

| ID | Threat | Impact | Likelihood | Mitigation | Status |
|----|--------|--------|------------|------------|--------|
| S-001 | Attacker forges JWT token | High | Low | RS256/EdDSA signature verification (FR-001) | ✓ Mitigated |
| S-002 | Session hijacking via token theft | High | Medium | Short token lifetime (≤15m), secure cookies, HTTPS only (FR-003) | ✓ Mitigated |
| S-003 | WebSocket origin spoofing | Medium | Low | Origin allowlist enforcement (FR-002) | ✓ Mitigated |
| S-004 | Replay attack with captured token | Medium | Low | Nonce/JTI replay protection (FR-001) | ✓ Mitigated |

### T - Tampering with Data

| ID | Threat | Impact | Likelihood | Mitigation | Status |
|----|--------|--------|------------|------------|--------|
| T-001 | MITM attack on data in transit | High | Low | TLS 1.2+ enforcement, HSTS preload (FR-003) | ✓ Mitigated |
| T-002 | Configuration file tampering | High | Low | File integrity monitoring, access controls | ⚠️ Partial |
| T-003 | Log file tampering | Medium | Low | Append-only logs, audit trail (FR-009) | ✓ Mitigated |
| T-004 | Frontend code injection | High | Medium | CSP blocking inline scripts, SRI for assets (FR-004) | ✓ Mitigated |

### R - Repudiation

| ID | Threat | Impact | Likelihood | Mitigation | Status |
|----|--------|--------|------------|------------|--------|
| R-001 | Admin denies destructive action | Medium | Low | Audit logs with correlation IDs (FR-009) | ✓ Mitigated |
| R-002 | User denies data export request | Low | Low | Audit trail for user actions (FR-010) | ✓ Mitigated |
| R-003 | Automated purge denies deletion | Medium | Low | Purge audit logging (SC-005) | ✓ Mitigated |

### I - Information Disclosure

| ID | Threat | Impact | Likelihood | Mitigation | Status |
|----|--------|--------|------------|------------|--------|
| I-001 | PII exposed in logs | High | High | PII redaction in logs (FR-009) | ✓ Mitigated |
| I-002 | Secrets in localStorage | High | Medium | Frontend storage validation (FR-011) | ✓ Mitigated |
| I-003 | Error messages leak system info | Medium | Medium | Generic error responses, no stack traces in production | ⚠️ Partial |
| I-004 | Token exposure in URL params | High | Low | Tokens in Authorization header only | ✓ Mitigated |
| I-005 | Raw audio data in logs | Medium | High | No raw payloads in logs (FR-009) | ✓ Mitigated |
| I-006 | Timing attacks on auth | Low | Low | Constant-time comparison for tokens | ✓ Mitigated |

### D - Denial of Service

| ID | Threat | Impact | Likelihood | Mitigation | Status |
|----|--------|--------|------------|------------|--------|
| D-001 | API rate limit exhaustion | High | High | Token + IP rate limiting (FR-007) | ✓ Mitigated |
| D-002 | WebSocket handshake flood | High | Medium | Connection caps per IP (FR-002) | ✓ Mitigated |
| D-003 | Large payload DoS | Medium | Medium | Request size limits | ⚠️ Partial |
| D-004 | Slowloris attack | Medium | Low | Connection timeout, reverse proxy protection | ✓ Mitigated |
| D-005 | CPU exhaustion via crypto | Medium | Low | Rate limiting, async processing | ✓ Mitigated |

### E - Elevation of Privilege

| ID | Threat | Impact | Likelihood | Mitigation | Status |
|----|--------|--------|------------|------------|--------|
| E-001 | JWT audience bypass | High | Low | Strict audience validation (FR-001) | ✓ Mitigated |
| E-002 | CSRF to admin actions | High | Medium | CSRF tokens for state changes (FR-006) | ✓ Mitigated |
| E-003 | Path traversal to read files | High | Low | Path sanitization, no user-controlled paths | ⚠️ Partial |
| E-004 | Prototype pollution in JS | Medium | Low | Input validation, CSP (FR-004) | ✓ Mitigated |

## Attack Scenarios

### Scenario 1: Unauthenticated WebSocket Attack

**Attack Steps:**
1. Attacker attempts to connect to `/ws/dashboard` without token
2. Origin header spoofed to allowed domain

**Defenses:**
1. Origin validation rejects mismatched origins (FR-002)
2. WebSocket expects auth message with valid JWT
3. No token → connection closed with 4401
4. Failed attempts logged for monitoring

**Result**: Attack blocked at multiple layers

### Scenario 2: Token Replay Attack

**Attack Steps:**
1. Attacker captures valid JWT token
2. Attempts to reuse token multiple times

**Defenses:**
1. JWT contains unique nonce/JTI (FR-001)
2. Nonce cache tracks used tokens
3. Replayed token rejected with 401
4. Replay attempt logged as security event

**Result**: Attack detected and blocked

### Scenario 3: Rate Limit Bypass

**Attack Steps:**
1. Attacker rotates IP addresses
2. Attempts to exhaust API with distributed requests

**Defenses:**
1. Token-based rate limiting (not just IP) (FR-007)
2. WebSocket connection caps per IP
3. Exponential backoff on 429 responses
4. CDN/WAF layer DDoS protection

**Result**: Attack mitigated with multiple strategies

### Scenario 4: XSS via Malicious Preset

**Attack Steps:**
1. Attacker crafts preset with `<script>` tag
2. Uploads preset to dashboard
3. Other users load malicious preset

**Defenses:**
1. CSP blocks inline scripts (FR-004)
2. Input sanitization on preset data
3. React/Vue framework XSS protections
4. No `eval()` or `dangerouslySetInnerHTML`

**Result**: XSS blocked by CSP and framework

## Mitigations Summary

### Implemented Controls

#### Authentication & Authorization
- ✓ JWT with RS256/EdDSA signatures (FR-001)
- ✓ Audience, expiration, nonce validation
- ✓ Clock skew tolerance (±60s)
- ✓ Token lifetime ≤15 minutes

#### Network Security
- ✓ TLS 1.2+ enforcement (FR-003)
- ✓ HSTS preload
- ✓ Origin allowlist for WebSocket (FR-002)
- ✓ CORS with credential support

#### Application Security
- ✓ CSP with strict policy (FR-004)
- ✓ CSRF protection (FR-006)
- ✓ Rate limiting (token + IP) (FR-007)
- ✓ Security headers (FR-005)

#### Data Protection
- ✓ PII redaction in logs (FR-009)
- ✓ No secrets in localStorage (FR-011)
- ✓ Encryption at rest (config/privacy.json)
- ✓ Retention policies (FR-010)

#### Monitoring & Response
- ✓ Structured logging with correlation IDs (FR-009)
- ✓ Audit trail for admin actions
- ✓ Security event tracking
- ✓ Automated purge with audit log

### Residual Risks

| Risk | Impact | Likelihood | Acceptance Rationale |
|------|--------|------------|---------------------|
| Advanced persistent threat (APT) | High | Very Low | Requires layered defense beyond application scope |
| Zero-day in dependencies | Medium | Low | Mitigated by regular scanning (FR-012), SBOM (FR-013) |
| Physical hardware access | High | Very Low | Out of scope for software controls |
| Social engineering | Medium | Low | Mitigated by training, MFA (future enhancement) |

## Security Requirements Traceability

| Requirement | STRIDE Categories | Implementation |
|-------------|-------------------|----------------|
| FR-001 (JWT Auth) | S, E | security_middleware.py:TokenValidator |
| FR-002 (WS Origin) | S, T | ws_gatekeeper.py:WebSocketGatekeeper |
| FR-003 (TLS) | T, I | config/security.yaml, Nginx config |
| FR-004 (CSP) | T, I | security_middleware.py:SecurityHeadersMiddleware |
| FR-005 (Headers) | T, I | security_middleware.py:SecurityHeadersMiddleware |
| FR-006 (CSRF) | E | security_middleware.py:CSRFProtection |
| FR-007 (Rate Limit) | D | security_middleware.py:RateLimiter |
| FR-009 (Logging) | R, I | privacy_manager.py:PIIRedactor |
| FR-010 (Retention) | I, R | privacy_manager.py:RetentionPolicy |
| FR-011 (Storage) | I | privacy_manager.py:validate_frontend_storage |

## Recommendations

### Immediate Actions
1. ✓ Implement all FR-001 through FR-011 controls
2. ✓ Deploy security headers and CSP
3. ✓ Enable audit logging
4. ⚠️ Set up automated security scanning (FR-012)

### Short-term (1-3 months)
1. Add multi-factor authentication (MFA)
2. Implement anomaly detection for auth patterns
3. Set up security dashboards and alerting
4. Conduct penetration testing

### Long-term (3-6 months)
1. Implement hardware security module (HSM) for key storage
2. Add behavioral analytics for anomaly detection
3. Implement zero-trust architecture
4. Regular security audits and threat model updates

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- STRIDE Methodology: https://docs.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats
- JWT Best Practices: https://tools.ietf.org/html/rfc8725
- WebSocket Security: https://www.rfc-editor.org/rfc/rfc6455.html#section-10
