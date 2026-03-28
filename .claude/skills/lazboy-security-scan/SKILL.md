---
name: lazboy-security-scan
description: "Perform automated security scanning on La-Z-Boy codebases. Covers SAST, dependency auditing, secret detection, OWASP Top 10 checks, and secure coding patterns. Use when reviewing code for security issues or setting up security automation in CI/CD."
version: "1.0.0"
category: Security
tags: [security, sast, owasp, scanning]
---

# La-Z-Boy Security Scan Skill

Automated security scanning standards for La-Z-Boy applications.

**Reference files — load when needed:**
- `references/owasp-checklist.md` — OWASP Top 10 compliance checklist
- `references/secure-patterns.md` — approved secure coding patterns

**Scripts — run when needed:**
- `scripts/security_scan.py` — run full security scan on codebase
- `scripts/detect_secrets.py` — scan for hardcoded secrets and credentials

---

## 1. OWASP Top 10 Checks

| # | Vulnerability | Check |
|---|---|---|
| A01 | Broken Access Control | Auth on all endpoints, RBAC enforced |
| A02 | Cryptographic Failures | TLS everywhere, secrets in vault |
| A03 | Injection | Parameterized queries, input validation |
| A04 | Insecure Design | Threat modeling, security requirements |
| A05 | Security Misconfiguration | No defaults, headers set, errors masked |
| A06 | Vulnerable Components | `npm audit`, `pip audit`, Snyk |
| A07 | Auth Failures | MFA, strong passwords, session management |
| A08 | Data Integrity | Signed updates, CI/CD pipeline security |
| A09 | Logging Failures | Security events logged, alerts configured |
| A10 | SSRF | URL validation, allowlists for external calls |

## 2. Automated Scans

### Dependency Audit
```bash
# JavaScript
npm audit --audit-level=high
npx better-npm-audit audit

# Python
pip audit
safety check
```

### Secret Detection
```bash
# Using gitleaks
gitleaks detect --source . --verbose

# Common patterns to detect
- AWS keys: AKIA[0-9A-Z]{16}
- Private keys: -----BEGIN (RSA|EC|DSA) PRIVATE KEY-----
- API tokens: [a-zA-Z0-9]{32,}
- Connection strings: (postgres|mysql|mongodb)://
```

### Static Analysis (SAST)
```bash
# JavaScript/TypeScript
npx eslint --plugin security .

# Python
bandit -r app/ -f json -o security-report.json
semgrep --config=p/owasp-top-ten .
```

## 3. Security Headers

Every HTTP response must include:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

## 4. Input Validation Rules

```typescript
// NEVER trust user input
const sanitize = (input: string): string => {
  return input
    .replace(/[<>]/g, '')    // Strip HTML tags
    .trim()
    .slice(0, 1000);          // Limit length
};

// SQL — always parameterized
// BAD:  `SELECT * FROM skills WHERE name = '${name}'`
// GOOD: `SELECT * FROM skills WHERE name = $1`, [name]
```

## 5. CI/CD Security Pipeline

```yaml
security:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Dependency audit
      run: npm audit --audit-level=high
    - name: Secret scan
      uses: gitleaks/gitleaks-action@v2
    - name: SAST scan
      uses: returntocorp/semgrep-action@v1
      with:
        config: p/owasp-top-ten
    - name: Container scan
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'app:latest'
        severity: 'HIGH,CRITICAL'
```

## 6. Incident Response

If a vulnerability is found:
1. **Assess severity** (Critical/High/Medium/Low)
2. **Contain** — disable affected endpoint if critical
3. **Fix** — patch within SLA (Critical: 24h, High: 72h)
4. **Verify** — re-scan to confirm fix
5. **Document** — update security log and postmortem
