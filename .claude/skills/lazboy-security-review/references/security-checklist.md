# Security Review Checklist

Comprehensive 10-domain security checklist for web applications with verification steps and code examples.

---

## Domain 1: Secrets Management

### Requirements

- [ ] No hardcoded secrets in source code (API keys, passwords, tokens)
- [ ] All secrets loaded from environment variables or a secrets manager
- [ ] `.env` files listed in `.gitignore`
- [ ] Secrets rotated on a regular schedule
- [ ] Different secrets per environment (dev, staging, production)

### Code Examples

```python
# BAD -- hardcoded secret
API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgresql://admin:password123@prod-db:5432/app"

# GOOD -- environment variables with validation
import os

API_KEY = os.environ["API_KEY"]  # Fails fast if missing
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")
```

```typescript
// GOOD -- fail-fast validation at startup
const requiredEnvVars = ["API_KEY", "DB_URL", "JWT_SECRET"] as const;
for (const key of requiredEnvVars) {
  if (!process.env[key]) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
}
```

### Verification

```bash
# Scan for hardcoded secrets
grep -rn "password\|secret\|api_key\|apikey\|token" --include="*.py" --include="*.ts" --include="*.js" .
# Check .gitignore
grep -q ".env" .gitignore && echo "OK" || echo "MISSING: .env not in .gitignore"
```

---

## Domain 2: XSS Prevention

### Requirements

- [ ] All user-generated content is escaped before rendering
- [ ] HTML sanitization library used for rich text (DOMPurify, bleach)
- [ ] Content Security Policy (CSP) headers configured
- [ ] No `dangerouslySetInnerHTML` or `v-html` without sanitization
- [ ] URL schemes validated (reject `javascript:`)

### Code Examples

```typescript
// BAD -- direct HTML insertion
element.innerHTML = userInput;

// GOOD -- sanitize with DOMPurify
import DOMPurify from "dompurify";
const clean = DOMPurify.sanitize(userInput, {
  ALLOWED_TAGS: ["b", "i", "em", "strong", "a", "p", "br"],
  ALLOWED_ATTR: ["href", "title"],
});

// GOOD -- React auto-escapes by default
function Comment({ text }: { text: string }) {
  return <p>{text}</p>;  // Safe -- React escapes this
}
```

```python
# GOOD -- Python bleach for HTML sanitization
import bleach

clean = bleach.clean(
    user_html,
    tags=["b", "i", "em", "strong", "a", "p"],
    attributes={"a": ["href", "title"]},
    strip=True,
)
```

### Verification

```bash
# Search for unsafe HTML insertion
grep -rn "innerHTML\|dangerouslySetInnerHTML\|v-html\|__html" --include="*.tsx" --include="*.jsx" --include="*.vue" .
```

---

## Domain 3: CSRF Protection

### Requirements

- [ ] CSRF tokens on all state-changing forms
- [ ] SameSite cookie attribute set to `Strict` or `Lax`
- [ ] Origin header validated on API requests
- [ ] Double-submit cookie pattern or synchronizer token pattern used

### Code Examples

```typescript
// Express CSRF middleware
import csrf from "csurf";

const csrfProtection = csrf({
  cookie: { sameSite: "strict", httpOnly: true, secure: true },
});

app.get("/form", csrfProtection, (req, res) => {
  res.render("form", { csrfToken: req.csrfToken() });
});

app.post("/submit", csrfProtection, (req, res) => {
  // Token validated automatically by middleware
  processForm(req.body);
});
```

```python
# Django -- CSRF is enabled by default
# Ensure middleware is present:
MIDDLEWARE = [
    "django.middleware.csrf.CsrfViewMiddleware",
    # ...
]

# In templates:
# <form method="post">{% csrf_token %} ... </form>
```

### Verification

- Check that all POST/PUT/DELETE routes have CSRF middleware.
- Inspect cookies for `SameSite` attribute.
- Review forms for CSRF token inclusion.

---

## Domain 4: SQL Injection Prevention

### Requirements

- [ ] All database queries use parameterized statements
- [ ] No string concatenation or f-strings in SQL queries
- [ ] ORM usage preferred over raw SQL
- [ ] Database user has minimum required permissions
- [ ] Input length limits enforced before query execution

### Code Examples

```python
# BAD -- SQL injection
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# GOOD -- parameterized query
cursor.execute("SELECT * FROM users WHERE name = %s", (user_input,))

# GOOD -- SQLAlchemy ORM
user = session.query(User).filter(User.name == user_input).first()

# GOOD -- asyncpg
row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
```

```typescript
// BAD -- string interpolation in SQL
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// GOOD -- parameterized query
const result = await pool.query("SELECT * FROM users WHERE id = $1", [userId]);

// GOOD -- Prisma ORM
const user = await prisma.user.findUnique({ where: { id: userId } });
```

### Verification

```bash
# Search for string interpolation in SQL
grep -rn "f\"SELECT\|f\"INSERT\|f\"UPDATE\|f\"DELETE" --include="*.py" .
grep -rn '`SELECT.*\${.*}`\|`INSERT.*\${.*}`' --include="*.ts" --include="*.js" .
```

---

## Domain 5: Authentication and Authorization

### Requirements

- [ ] Passwords hashed with bcrypt, scrypt, or Argon2 (never MD5/SHA1)
- [ ] Session tokens are cryptographically random
- [ ] JWT tokens have short expiry (15-60 minutes)
- [ ] Refresh tokens stored securely and rotated on use
- [ ] Authorization checked at every endpoint (not just the frontend)
- [ ] Row-level security enforced at the data layer

### Code Examples

```python
# GOOD -- password hashing with bcrypt
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

```typescript
// GOOD -- JWT with short expiry
import jwt from "jsonwebtoken";

function generateTokens(userId: string) {
  const accessToken = jwt.sign({ sub: userId }, process.env.JWT_SECRET!, {
    expiresIn: "15m",
  });
  const refreshToken = jwt.sign({ sub: userId }, process.env.REFRESH_SECRET!, {
    expiresIn: "7d",
  });
  return { accessToken, refreshToken };
}

// GOOD -- middleware authorization check
function requireRole(role: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (req.user?.role !== role) {
      return res.status(403).json({ error: "Forbidden" });
    }
    next();
  };
}
```

### Verification

- [ ] Confirm password storage uses bcrypt/scrypt/argon2.
- [ ] Check JWT expiry is under 60 minutes.
- [ ] Verify every route handler checks authorization.

---

## Domain 6: Rate Limiting

### Requirements

- [ ] Global rate limit on all API endpoints
- [ ] Stricter limits on authentication endpoints (login, register, password reset)
- [ ] Rate limit headers returned to clients (X-RateLimit-*)
- [ ] Distributed rate limiting if running multiple instances (Redis-backed)
- [ ] Account lockout after repeated failed attempts

### Code Examples

```typescript
import rateLimit from "express-rate-limit";
import RedisStore from "rate-limit-redis";

// General API limit
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  message: { error: "Too many requests" },
});

// Strict auth limit
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  message: { error: "Too many login attempts, try again later" },
});

app.use("/api/", apiLimiter);
app.use("/api/auth/", authLimiter);
```

```python
# FastAPI rate limiting with slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("5/15minutes")
async def login(request: Request):
    ...
```

### Verification

- [ ] Test that exceeding the limit returns HTTP 429.
- [ ] Verify rate limit applies per-IP or per-user as intended.

---

## Domain 7: Input Validation

### Requirements

- [ ] All user input validated with a schema (Zod, Pydantic, Joi)
- [ ] Validation happens server-side (client-side validation is optional UX)
- [ ] File uploads validated: type, size, filename sanitized
- [ ] Numeric inputs have min/max bounds
- [ ] String inputs have max length
- [ ] Reject unexpected fields (strict schemas)

### Code Examples

```python
# GOOD -- Pydantic validation
from pydantic import BaseModel, Field, EmailStr

class CreateUserRequest(BaseModel, extra="forbid"):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=150)

@app.post("/api/users")
async def create_user(data: CreateUserRequest):
    # data is already validated
    ...
```

```typescript
// GOOD -- Zod validation
import { z } from "zod";

const createUserSchema = z.object({
  email: z.string().email().max(255),
  name: z.string().min(1).max(100).trim(),
  age: z.number().int().min(0).max(150),
}).strict();  // Reject unknown fields

app.post("/api/users", (req, res) => {
  const result = createUserSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({ errors: result.error.flatten() });
  }
  // result.data is typed and validated
});
```

### Verification

- [ ] Every endpoint that reads `req.body` or `request.json` uses schema validation.
- [ ] File upload endpoints validate MIME type, size, and sanitize filename.

---

## Domain 8: CORS Configuration

### Requirements

- [ ] CORS origin restricted to known domains (never `*` in production)
- [ ] Credentials mode requires explicit origin (not wildcard)
- [ ] Only necessary HTTP methods allowed
- [ ] Preflight responses cached appropriately
- [ ] Sensitive endpoints restrict CORS further

### Code Examples

```typescript
import cors from "cors";

// BAD -- wide open
app.use(cors());

// GOOD -- restricted
app.use(cors({
  origin: ["https://app.example.com", "https://admin.example.com"],
  methods: ["GET", "POST", "PUT", "DELETE"],
  credentials: true,
  maxAge: 86400,
}));
```

```python
# FastAPI CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=86400,
)
```

### Verification

```bash
curl -I -X OPTIONS -H "Origin: https://evil.com" https://api.example.com/endpoint
# Should NOT return Access-Control-Allow-Origin: https://evil.com
```

---

## Domain 9: Content Security Policy (CSP)

### Requirements

- [ ] CSP header set with restrictive `default-src`
- [ ] No `unsafe-inline` for scripts (use nonces or hashes)
- [ ] No `unsafe-eval` in production
- [ ] `frame-ancestors` set to prevent clickjacking
- [ ] Report URI configured for CSP violations

### Code Examples

```typescript
// GOOD -- Helmet.js for Express
import helmet from "helmet";

app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'", "'nonce-abc123'"],
    styleSrc: ["'self'", "'unsafe-inline'"],  // CSS inline is lower risk
    imgSrc: ["'self'", "data:", "https://cdn.example.com"],
    connectSrc: ["'self'", "https://api.example.com"],
    frameAncestors: ["'none'"],
    reportUri: "/csp-report",
  },
}));
```

```python
# Django CSP with django-csp
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https://cdn.example.com")
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_REPORT_URI = "/csp-report/"
```

### Verification

```bash
curl -I https://app.example.com | grep -i "content-security-policy"
# Should see a restrictive CSP header
```

---

## Domain 10: Dependency Security

### Requirements

- [ ] `npm audit` / `pip-audit` / `safety check` run in CI pipeline
- [ ] No critical or high severity vulnerabilities in production dependencies
- [ ] Lock files committed (package-lock.json, poetry.lock, uv.lock)
- [ ] Dependabot or Renovate configured for automated updates
- [ ] New dependencies reviewed before adoption (license, maintenance, popularity)
- [ ] Minimal dependency principle -- avoid unnecessary packages

### Code Examples

```bash
# Node.js
npm audit --production
npx audit-ci --critical

# Python
pip-audit
safety check -r requirements.txt

# Both -- in CI
# .github/workflows/security.yml
# - name: Audit dependencies
#   run: npm audit --audit-level=high
```

```yaml
# Dependabot configuration -- .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

### Verification

- [ ] CI pipeline fails on critical vulnerabilities.
- [ ] Lock files are present and committed.
- [ ] Automated dependency updates are active.
