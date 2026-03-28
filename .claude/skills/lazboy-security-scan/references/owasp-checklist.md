# OWASP Top 10 (2021) Security Checklist

Comprehensive checklist with detection methods, prevention strategies, and code examples for each OWASP Top 10 category.

---

## A01:2021 -- Broken Access Control

### Description

Access control enforces policy so users cannot act outside their intended permissions. Failures lead to unauthorized information disclosure, modification, or destruction of data.

### How to Detect

- [ ] Attempt accessing other users' resources by modifying IDs in URLs/API calls (IDOR)
- [ ] Try accessing admin endpoints without authentication/authorization
- [ ] Test CORS configuration for overly permissive origins
- [ ] Check for missing access control checks on API endpoints
- [ ] Verify that file metadata (e.g., directory listing) is not exposed
- [ ] Test for path traversal in file access endpoints

### How to Prevent

- [ ] Deny by default (except for public resources)
- [ ] Implement access control mechanisms once, reuse throughout the application
- [ ] Enforce record ownership rather than accepting user-submitted record IDs
- [ ] Disable directory listing on web servers
- [ ] Log access control failures and alert on repeated failures
- [ ] Rate-limit API and controller access

### Code Examples

**Vulnerable:**

```python
# Direct Object Reference -- user can access any order
@app.route('/api/orders/<order_id>')
def get_order(order_id):
    order = db.orders.find_one({'_id': order_id})
    return jsonify(order)
```

**Fixed:**

```python
@app.route('/api/orders/<order_id>')
@login_required
def get_order(order_id):
    order = db.orders.find_one({
        '_id': order_id,
        'user_id': current_user.id  # Enforce ownership
    })
    if not order:
        abort(404)
    return jsonify(order)
```

---

## A02:2021 -- Cryptographic Failures

### Description

Failures related to cryptography (or lack thereof) that lead to exposure of sensitive data: passwords, credit card numbers, health records, personal information, or business secrets.

### How to Detect

- [ ] Identify data transmitted or stored in cleartext
- [ ] Check for deprecated cryptographic algorithms (MD5, SHA1, DES, RC4)
- [ ] Verify TLS configuration (version, cipher suites)
- [ ] Check if encryption keys are hardcoded or use weak key derivation
- [ ] Examine if sensitive data is cached or logged
- [ ] Check if passwords are hashed with a strong, salted algorithm

### How to Prevent

- [ ] Classify data processed, stored, or transmitted and identify sensitive data
- [ ] Encrypt all sensitive data at rest and in transit
- [ ] Use strong, current algorithms (AES-256, RSA-2048+, SHA-256+)
- [ ] Use authenticated encryption (AES-GCM, ChaCha20-Poly1305)
- [ ] Store passwords with bcrypt, scrypt, argon2, or PBKDF2
- [ ] Disable caching for sensitive data responses
- [ ] Do not use deprecated protocols (SSLv3, TLS 1.0, TLS 1.1)

### Code Examples

**Vulnerable:**

```python
import hashlib

# MD5 for password storage -- INSECURE
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
```

**Fixed:**

```python
import bcrypt

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed)
```

---

## A03:2021 -- Injection

### Description

User-supplied data is sent to an interpreter as part of a command or query. SQL injection, NoSQL injection, OS command injection, LDAP injection.

### How to Detect

- [ ] Test input fields with SQL injection payloads (`' OR 1=1 --`, `'; DROP TABLE`)
- [ ] Check for string concatenation in queries
- [ ] Look for calls to `eval()`, `exec()`, `os.system()`, `subprocess.call(shell=True)`
- [ ] Test for template injection (SSTI)
- [ ] Check ORM usage for raw query patterns

### How to Prevent

- [ ] Use parameterized queries / prepared statements for all database access
- [ ] Use ORM query builders instead of raw SQL
- [ ] Validate and sanitize all input (server-side)
- [ ] Escape special characters for the specific interpreter
- [ ] Use LIMIT and other SQL controls to prevent mass disclosure
- [ ] Never pass user input to shell commands

### Code Examples

**Vulnerable:**

```python
# SQL Injection via string concatenation
def get_user(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return db.execute(query)
```

**Fixed:**

```python
# Parameterized query
def get_user(username):
    query = "SELECT * FROM users WHERE username = %s"
    return db.execute(query, (username,))

# ORM approach
def get_user(username):
    return User.query.filter_by(username=username).first()
```

---

## A04:2021 -- Insecure Design

### Description

Flaws in design and architecture rather than implementation. Represents missing or ineffective security controls that were never created as part of the design.

### How to Detect

- [ ] Review threat model for missing security controls
- [ ] Check for missing rate limiting on sensitive operations
- [ ] Verify business logic controls (e.g., purchase limits, transfer verification)
- [ ] Look for missing multi-factor authentication on critical operations
- [ ] Check for unrestricted resource consumption

### How to Prevent

- [ ] Establish secure development lifecycle with security requirements
- [ ] Use threat modeling for authentication, access control, business logic
- [ ] Integrate security language and controls into user stories
- [ ] Write unit and integration tests to validate security controls
- [ ] Separate tier layers (presentation, business, data)
- [ ] Limit resource consumption by user or service

### Code Examples

**Vulnerable:**

```python
# No rate limiting on password reset
@app.route('/api/password-reset', methods=['POST'])
def password_reset():
    email = request.json['email']
    send_reset_email(email)  # Can be abused for email bombing
    return jsonify({'status': 'sent'})
```

**Fixed:**

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/api/password-reset', methods=['POST'])
@limiter.limit("3 per hour")
def password_reset():
    email = request.json['email']
    # Don't reveal if email exists
    if user := User.query.filter_by(email=email).first():
        send_reset_email(user)
    return jsonify({'status': 'If the email exists, a reset link was sent.'})
```

---

## A05:2021 -- Security Misconfiguration

### Description

Missing security hardening, unnecessary features enabled, default accounts/passwords, overly informative error messages, misconfigured security headers.

### How to Detect

- [ ] Check for default credentials
- [ ] Verify security headers (CSP, X-Frame-Options, HSTS, etc.)
- [ ] Check for stack traces or detailed errors in production
- [ ] Look for unnecessary services, ports, or features enabled
- [ ] Verify that directory listing is disabled
- [ ] Check cloud storage permissions (S3 buckets, etc.)
- [ ] Examine CORS configuration

### How to Prevent

- [ ] Automated hardening process for deployment
- [ ] Minimal platform: remove unused features, components, documentation
- [ ] Review and update configurations as part of patch management
- [ ] Implement proper security headers
- [ ] Use a segmented application architecture
- [ ] Send security directives to clients (e.g., CSP headers)

### Code Examples

**Vulnerable:**

```python
# Debug mode in production, verbose errors
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'development-key'
```

**Fixed:**

```python
import os

app = Flask(__name__)
app.config['DEBUG'] = False
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '0'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
```

---

## A06:2021 -- Vulnerable and Outdated Components

### Description

Using components (libraries, frameworks, OS) with known vulnerabilities. Includes cases where you don't know the versions of all components or don't scan for vulnerabilities regularly.

### How to Detect

- [ ] Run `npm audit` / `pip-audit` / `safety check` regularly
- [ ] Check CVE databases for known vulnerabilities in dependencies
- [ ] Identify components that are no longer maintained
- [ ] Use SCA tools (Snyk, Dependabot, Renovate)
- [ ] Verify all component versions are tracked

### How to Prevent

- [ ] Remove unused dependencies, features, and files
- [ ] Continuously inventory component versions (SBOM)
- [ ] Monitor CVE and NVD for vulnerabilities
- [ ] Use automated tools to detect vulnerabilities in dependencies
- [ ] Only obtain components from official sources over secure links
- [ ] Prefer signed packages; verify integrity

### Code Examples

```json
// package.json -- vulnerable version
{
  "dependencies": {
    "lodash": "4.17.15"  // CVE-2020-8203: Prototype Pollution
  }
}

// Fixed
{
  "dependencies": {
    "lodash": "^4.17.21"  // Patched version
  }
}
```

```bash
# Audit commands
npm audit
npm audit fix
pip-audit
safety check -r requirements.txt
```

---

## A07:2021 -- Identification and Authentication Failures

### Description

Weaknesses in authentication: allowing brute force, weak passwords, improper session management, credential exposure, missing MFA.

### How to Detect

- [ ] Test for brute force resistance (account lockout, rate limiting)
- [ ] Check for default/weak password policies
- [ ] Verify session timeout and invalidation
- [ ] Test for session fixation
- [ ] Check if credentials are sent over unencrypted connections
- [ ] Verify password storage mechanism

### How to Prevent

- [ ] Implement multi-factor authentication
- [ ] Enforce strong password policies (length > 8, check against breached passwords)
- [ ] Use bcrypt/argon2/scrypt for password hashing
- [ ] Limit failed login attempts with progressive delays
- [ ] Use server-side session management with random session IDs
- [ ] Invalidate sessions on logout, password change, and timeout

### Code Examples

**Vulnerable:**

```javascript
// No rate limiting, plain text password comparison
app.post('/login', (req, res) => {
  const user = db.findUser(req.body.username);
  if (user && user.password === req.body.password) {
    req.session.userId = user.id;
    res.json({ success: true });
  }
});
```

**Fixed:**

```javascript
import bcrypt from 'bcrypt';
import rateLimit from 'express-rate-limit';

const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutes
  max: 5,                     // 5 attempts per window
  message: 'Too many login attempts. Try again later.',
});

app.post('/login', loginLimiter, async (req, res) => {
  const user = await db.findUser(req.body.username);
  if (!user) {
    // Same response for invalid user to prevent enumeration
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  const valid = await bcrypt.compare(req.body.password, user.passwordHash);
  if (!valid) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  // Regenerate session to prevent fixation
  req.session.regenerate((err) => {
    req.session.userId = user.id;
    res.json({ success: true });
  });
});
```

---

## A08:2021 -- Software and Data Integrity Failures

### Description

Code and infrastructure that does not protect against integrity violations: insecure CI/CD pipelines, auto-update without verification, insecure deserialization, unverified dependencies.

### How to Detect

- [ ] Check if dependencies are pulled from trusted sources
- [ ] Verify CI/CD pipeline security (code review, access controls)
- [ ] Look for deserialization of untrusted data
- [ ] Check for unsigned software updates
- [ ] Verify integrity of data in transit

### How to Prevent

- [ ] Use digital signatures to verify software/data integrity
- [ ] Ensure libraries are pulled from trusted repositories
- [ ] Use SCA tools to verify components don't contain known vulnerabilities
- [ ] Ensure CI/CD pipeline has proper access control and segregation
- [ ] Do not send unsigned or unencrypted serialized data to untrusted clients
- [ ] Use Subresource Integrity (SRI) for CDN resources

### Code Examples

**Vulnerable:**

```python
import pickle

# Deserializing untrusted data -- allows arbitrary code execution
@app.route('/api/data', methods=['POST'])
def receive_data():
    data = pickle.loads(request.data)  # DANGEROUS
    return process(data)
```

**Fixed:**

```python
import json

@app.route('/api/data', methods=['POST'])
def receive_data():
    data = json.loads(request.data)  # Safe deserialization
    # Validate schema
    validated = DataSchema().load(data)
    return process(validated)
```

---

## A09:2021 -- Security Logging and Monitoring Failures

### Description

Without logging and monitoring, breaches cannot be detected. Insufficient logging, detection, monitoring, and active response allows attackers to persist in the system.

### How to Detect

- [ ] Verify that login/access control/input validation failures are logged
- [ ] Check that logs have sufficient detail for forensics
- [ ] Ensure logs are not only stored locally
- [ ] Verify alerting thresholds and response procedures exist
- [ ] Check for log injection vulnerabilities
- [ ] Verify logs don't contain sensitive data (passwords, tokens)

### How to Prevent

- [ ] Log all authentication events (success, failure, lockout)
- [ ] Log all access control failures
- [ ] Log high-value transactions with integrity controls
- [ ] Ensure log entries have enough context (who, what, when, where)
- [ ] Use centralized log management (ELK, Splunk, CloudWatch)
- [ ] Establish monitoring and alerting for suspicious activities
- [ ] Create incident response and recovery plan

### Code Examples

**Vulnerable:**

```python
# No logging of security events
@app.route('/login', methods=['POST'])
def login():
    user = authenticate(request.json)
    if not user:
        return jsonify({'error': 'Invalid'}), 401
    return create_session(user)
```

**Fixed:**

```python
import logging
import structlog

logger = structlog.get_logger()

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', '')
    user = authenticate(request.json)

    if not user:
        logger.warning(
            'authentication_failure',
            username=username,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
        )
        return jsonify({'error': 'Invalid credentials'}), 401

    logger.info(
        'authentication_success',
        user_id=user.id,
        ip_address=request.remote_addr,
    )
    return create_session(user)
```

---

## A10:2021 -- Server-Side Request Forgery (SSRF)

### Description

SSRF occurs when a web application fetches a remote resource without validating the user-supplied URL. It allows an attacker to force the application to make requests to internal resources.

### How to Detect

- [ ] Identify features that fetch URLs provided by users (webhooks, URL previews, file imports)
- [ ] Test with internal IP addresses (127.0.0.1, 169.254.169.254, 10.x.x.x)
- [ ] Test with DNS rebinding attacks
- [ ] Check for URL schema restrictions (file://, gopher://)
- [ ] Test cloud metadata endpoints (169.254.169.254)

### How to Prevent

- [ ] Validate and sanitize all user-supplied URLs
- [ ] Use an allowlist of permitted domains/IPs
- [ ] Block requests to private IP ranges and metadata endpoints
- [ ] Do not send raw responses to the client
- [ ] Disable HTTP redirections
- [ ] Use network-level segmentation (firewall rules)

### Code Examples

**Vulnerable:**

```python
import requests

# Fetches any URL including internal resources
@app.route('/api/fetch-url')
def fetch_url():
    url = request.args.get('url')
    response = requests.get(url)  # SSRF: can access internal services
    return response.text
```

**Fixed:**

```python
import ipaddress
import requests
from urllib.parse import urlparse

ALLOWED_SCHEMES = {'http', 'https'}
BLOCKED_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),  # Cloud metadata
]

def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        return not any(ip in network for network in BLOCKED_NETWORKS)
    except ValueError:
        # Hostname, not IP -- resolve and check
        import socket
        try:
            resolved_ip = socket.gethostbyname(parsed.hostname)
            ip = ipaddress.ip_address(resolved_ip)
            return not any(ip in network for network in BLOCKED_NETWORKS)
        except socket.gaierror:
            return False

@app.route('/api/fetch-url')
def fetch_url():
    url = request.args.get('url')
    if not is_safe_url(url):
        abort(400, 'URL not allowed')
    response = requests.get(url, timeout=5, allow_redirects=False)
    return response.text
```
