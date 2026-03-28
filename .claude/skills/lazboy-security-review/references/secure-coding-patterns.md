# Secure Coding Patterns Reference

Safe coding patterns for each major vulnerability type, with concrete examples in Python and TypeScript/JavaScript.

---

## 1. Parameterized Queries (SQL Injection Prevention)

### The Problem

String interpolation in SQL allows attackers to inject arbitrary queries.

```python
# VULNERABLE
query = f"SELECT * FROM users WHERE email = '{email}'"
# Input: ' OR '1'='1' --
# Result: SELECT * FROM users WHERE email = '' OR '1'='1' --'
```

### Safe Patterns

```python
# Python -- psycopg2
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))

# Python -- SQLAlchemy Core
stmt = select(users).where(users.c.email == email)
result = connection.execute(stmt)

# Python -- SQLAlchemy ORM
user = session.query(User).filter(User.email == email).first()

# Python -- asyncpg
row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)

# Python -- Django ORM
user = User.objects.filter(email=email).first()
# Django raw queries -- still parameterized
User.objects.raw("SELECT * FROM users WHERE email = %s", [email])
```

```typescript
// Node.js -- pg (node-postgres)
const { rows } = await pool.query("SELECT * FROM users WHERE email = $1", [email]);

// Prisma
const user = await prisma.user.findUnique({ where: { email } });

// Drizzle
const user = await db.select().from(users).where(eq(users.email, email));

// Knex
const user = await knex("users").where({ email }).first();
```

### Stored Procedures for Complex Queries

```sql
CREATE FUNCTION search_users(search_term TEXT, max_results INT)
RETURNS SETOF users AS $$
  SELECT * FROM users
  WHERE name ILIKE '%' || search_term || '%'
  LIMIT max_results;
$$ LANGUAGE sql SECURITY DEFINER;
```

---

## 2. Output Encoding (XSS Prevention)

### The Problem

Rendering unescaped user input in HTML allows script injection.

### Safe Patterns -- Context-Specific Encoding

```typescript
// HTML context -- escape entities
function escapeHtml(str: string): string {
  const map: Record<string, string> = {
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;",
  };
  return str.replace(/[&<>"']/g, (c) => map[c]);
}

// URL context -- encode components
const safeUrl = `https://example.com/search?q=${encodeURIComponent(userQuery)}`;

// JavaScript context -- JSON encode
const safeData = JSON.stringify(userData);
// In template: <script>const data = ${safeData};</script>

// CSS context -- escape and validate
function escapeCss(str: string): string {
  return str.replace(/[^\w-]/g, (c) => `\\${c.charCodeAt(0).toString(16)} `);
}
```

```python
# Python -- Jinja2 (auto-escapes by default)
# In template: {{ user_input }}  -- auto-escaped
# For explicit: {{ user_input | e }}

# Python -- manual escaping
from markupsafe import escape
safe_output = escape(user_input)

# Python -- bleach for rich text
import bleach
clean_html = bleach.clean(
    user_html,
    tags=["b", "i", "a", "p", "br", "ul", "li"],
    attributes={"a": ["href", "title"]},
    protocols=["http", "https", "mailto"],
    strip=True,
)
```

### URL Validation

```typescript
// Prevent javascript: and data: URL schemes
function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ["http:", "https:", "mailto:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}
```

---

## 3. CSRF Tokens

### Synchronizer Token Pattern

```typescript
import crypto from "crypto";

// Generate token per session
function generateCsrfToken(): string {
  return crypto.randomBytes(32).toString("hex");
}

// Middleware to verify
function verifyCsrf(req: Request, res: Response, next: NextFunction) {
  const token = req.headers["x-csrf-token"] || req.body._csrf;
  if (!token || token !== req.session.csrfToken) {
    return res.status(403).json({ error: "Invalid CSRF token" });
  }
  next();
}

// Set token in session
app.use((req, res, next) => {
  if (!req.session.csrfToken) {
    req.session.csrfToken = generateCsrfToken();
  }
  res.locals.csrfToken = req.session.csrfToken;
  next();
});
```

### Double-Submit Cookie Pattern

```typescript
// Set CSRF cookie (not httpOnly -- JS needs to read it)
res.cookie("csrf-token", csrfToken, {
  sameSite: "strict",
  secure: true,
  httpOnly: false,  // Client JS reads this
});

// Client sends it in a header
fetch("/api/action", {
  method: "POST",
  headers: { "X-CSRF-Token": getCookie("csrf-token") },
  body: JSON.stringify(data),
});

// Server compares cookie value with header value
function verifyCsrf(req: Request, res: Response, next: NextFunction) {
  const cookieToken = req.cookies["csrf-token"];
  const headerToken = req.headers["x-csrf-token"];
  if (!cookieToken || cookieToken !== headerToken) {
    return res.status(403).json({ error: "CSRF validation failed" });
  }
  next();
}
```

### SameSite Cookies (Defense in Depth)

```typescript
// SameSite=Strict prevents the browser from sending the cookie
// on cross-origin requests, providing inherent CSRF protection
res.cookie("session", token, {
  httpOnly: true,
  secure: true,
  sameSite: "strict",
  maxAge: 3600000,
});
```

---

## 4. Secure Headers

### Complete Header Configuration

```typescript
import helmet from "helmet";

app.use(helmet());  // Sets many secure headers by default

// Or configure individually:
app.use((req, res, next) => {
  // Prevent MIME type sniffing
  res.setHeader("X-Content-Type-Options", "nosniff");
  // Prevent clickjacking
  res.setHeader("X-Frame-Options", "DENY");
  // Control referrer information
  res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
  // Enforce HTTPS
  res.setHeader("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload");
  // Disable browser features you don't use
  res.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  // CSP
  res.setHeader("Content-Security-Policy",
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data: https:; frame-ancestors 'none';"
  );
  next();
});
```

```python
# Django security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
```

```python
# FastAPI with custom middleware
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI(middleware=[
    Middleware(TrustedHostMiddleware, allowed_hosts=["app.example.com"]),
])

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

## 5. Password Hashing

### Recommended Algorithms (in order of preference)

1. **Argon2id** -- memory-hard, GPU-resistant (best choice)
2. **bcrypt** -- widely supported, well-tested
3. **scrypt** -- memory-hard, good alternative

### Argon2 (Recommended)

```python
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,        # Number of iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,      # Number of threads
)

hashed = ph.hash("user_password")
# $argon2id$v=19$m=65536,t=3,p=4$...

try:
    ph.verify(hashed, "user_password")
    if ph.check_needs_rehash(hashed):
        new_hash = ph.hash("user_password")  # Upgrade hash params
except argon2.exceptions.VerifyMismatchError:
    raise AuthenticationError("Invalid password")
```

### bcrypt

```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
```

```typescript
import bcrypt from "bcrypt";

const SALT_ROUNDS = 12;

async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, SALT_ROUNDS);
}

async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}
```

### Never Use

- MD5, SHA1, SHA256 (fast hashes -- unsuitable for passwords)
- Unsalted hashes
- Custom/homebrew hashing schemes

---

## 6. JWT Best Practices

### Token Generation

```typescript
import jwt from "jsonwebtoken";

interface TokenPayload {
  sub: string;      // Subject (user ID)
  role: string;     // Authorization role
  iat: number;      // Issued at
  exp: number;      // Expiration
  jti: string;      // Unique token ID (for revocation)
}

function generateAccessToken(userId: string, role: string): string {
  return jwt.sign(
    { sub: userId, role, jti: crypto.randomUUID() },
    process.env.JWT_SECRET!,
    {
      expiresIn: "15m",
      algorithm: "HS256",
      issuer: "app.example.com",
      audience: "app.example.com",
    }
  );
}
```

### Token Verification

```typescript
function verifyToken(token: string): TokenPayload {
  return jwt.verify(token, process.env.JWT_SECRET!, {
    algorithms: ["HS256"],   // Prevent algorithm confusion attacks
    issuer: "app.example.com",
    audience: "app.example.com",
    clockTolerance: 30,      // 30 seconds leeway
  }) as TokenPayload;
}
```

### Key Rules

- Always specify the algorithm in `verify()` to prevent `none` algorithm attacks.
- Use short expiry for access tokens (15 minutes).
- Store refresh tokens server-side (database) with ability to revoke.
- Never store JWTs in localStorage (XSS risk). Use httpOnly cookies.
- Rotate signing keys periodically.
- Include `jti` claim for token revocation capability.

### Refresh Token Rotation

```typescript
async function refreshTokens(refreshToken: string) {
  // 1. Verify the refresh token
  const payload = verifyToken(refreshToken);

  // 2. Check if token is in the allowlist (database)
  const stored = await db.refreshToken.findUnique({ where: { jti: payload.jti } });
  if (!stored || stored.revoked) {
    // Potential token reuse -- revoke entire family
    await db.refreshToken.updateMany({
      where: { userId: payload.sub },
      data: { revoked: true },
    });
    throw new Error("Token reuse detected");
  }

  // 3. Revoke old token and issue new pair
  await db.refreshToken.update({ where: { jti: payload.jti }, data: { revoked: true } });

  const newAccess = generateAccessToken(payload.sub, payload.role);
  const newRefresh = generateRefreshToken(payload.sub);
  return { accessToken: newAccess, refreshToken: newRefresh };
}
```

---

## 7. Path Traversal Prevention

```python
from pathlib import Path

UPLOAD_DIR = Path("/app/uploads").resolve()

def safe_file_access(filename: str) -> Path:
    """Resolve the path and verify it stays within the allowed directory."""
    requested = (UPLOAD_DIR / filename).resolve()
    if not requested.is_relative_to(UPLOAD_DIR):
        raise ValueError("Path traversal detected")
    return requested

# BAD
# open(f"/app/uploads/{user_filename}")  # ../../etc/passwd

# GOOD
path = safe_file_access(user_filename)
with open(path) as f:
    return f.read()
```

```typescript
import path from "path";

const UPLOAD_DIR = path.resolve("/app/uploads");

function safePath(filename: string): string {
  const resolved = path.resolve(UPLOAD_DIR, filename);
  if (!resolved.startsWith(UPLOAD_DIR + path.sep)) {
    throw new Error("Path traversal detected");
  }
  return resolved;
}
```

---

## 8. Secure File Upload

```python
import os
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def secure_upload(file_data: bytes, original_name: str, content_type: str) -> str:
    """Validate and store an uploaded file securely."""
    # 1. Check size
    if len(file_data) > MAX_FILE_SIZE:
        raise ValueError(f"File exceeds {MAX_FILE_SIZE} byte limit")

    # 2. Validate extension
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type '{ext}' not allowed")

    # 3. Generate safe filename (never use user-provided name)
    safe_name = f"{uuid.uuid4().hex}{ext}"

    # 4. Validate content type matches extension
    expected_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".pdf": "application/pdf",
    }
    if content_type != expected_types.get(ext):
        raise ValueError("Content type does not match file extension")

    # 5. Store file
    dest = Path("/app/uploads") / safe_name
    dest.write_bytes(file_data)
    return safe_name
```

---

## 9. Logging and Error Handling

```python
import logging

logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "ssn", "credit_card"}

def redact_sensitive(data: dict) -> dict:
    """Redact sensitive fields before logging."""
    return {
        k: "[REDACTED]" if any(s in k.lower() for s in SENSITIVE_FIELDS) else v
        for k, v in data.items()
    }

# In error handlers -- generic message to user, details in logs
try:
    result = process_payment(order)
except PaymentError as e:
    logger.error("Payment failed", extra={"order_id": order.id, "error": str(e)})
    # Never expose internal details to the user
    raise HTTPException(status_code=500, detail="Payment processing failed")
```

```typescript
// Express error handler -- generic response, detailed logs
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error("Unhandled error:", {
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
    userId: req.user?.id,
  });

  // Never send stack traces or internal details to clients
  res.status(500).json({ error: "An unexpected error occurred" });
});
```

---

## 10. Summary: Defense in Depth

| Layer | Pattern |
|-------|---------|
| Input | Schema validation (Zod, Pydantic) |
| Query | Parameterized statements / ORM |
| Output | Context-aware encoding / sanitization |
| Auth | bcrypt/argon2, short-lived JWTs |
| Session | httpOnly + Secure + SameSite cookies |
| Transport | HTTPS + HSTS |
| Headers | CSP, X-Frame-Options, CORP |
| Files | Extension whitelist, random names, path validation |
| Errors | Generic messages, redacted logs |
| Dependencies | Automated auditing, lock files |
