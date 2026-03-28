# Secure Coding Patterns

Practical, copy-paste-ready patterns for common security requirements.

---

## Table of Contents

1. [Input Validation](#1-input-validation)
2. [Output Encoding](#2-output-encoding)
3. [Parameterized Queries](#3-parameterized-queries)
4. [Session Management](#4-session-management)
5. [Password Hashing](#5-password-hashing)
6. [JWT Best Practices](#6-jwt-best-practices)
7. [CORS Configuration](#7-cors-configuration)
8. [Content Security Policy](#8-content-security-policy)
9. [Secure File Upload](#9-secure-file-upload)

---

## 1. Input Validation

**Principle**: Validate all input on the server side. Use allowlisting (defining what IS allowed) over denylisting (defining what is NOT allowed).

### Allowlisting vs. Denylisting

| Approach | Description | Effectiveness |
|----------|-------------|---------------|
| **Allowlisting** | Define exactly what is permitted | Strong -- rejects unknown patterns |
| **Denylisting** | Define what is forbidden | Weak -- attackers find bypasses |

### Python (Flask/FastAPI)

```python
import re
from pydantic import BaseModel, validator, constr, conint
from typing import Literal

# Pydantic model with allowlist validation
class CreateUserRequest(BaseModel):
    username: constr(min_length=3, max_length=30, pattern=r'^[a-zA-Z0-9_]+$')
    email: constr(max_length=254, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    role: Literal['user', 'editor']  # Allowlist of valid roles
    age: conint(ge=13, le=150)

    @validator('username')
    def username_not_reserved(cls, v):
        reserved = {'admin', 'root', 'system', 'null', 'undefined'}
        if v.lower() in reserved:
            raise ValueError('Reserved username')
        return v

# Usage with FastAPI
@app.post('/api/users')
async def create_user(request: CreateUserRequest):
    # request is already validated
    pass
```

### JavaScript/TypeScript (Zod)

```typescript
import { z } from 'zod';

const createUserSchema = z.object({
  username: z.string()
    .min(3).max(30)
    .regex(/^[a-zA-Z0-9_]+$/, 'Alphanumeric and underscores only'),
  email: z.string().email().max(254),
  role: z.enum(['user', 'editor']),
  age: z.number().int().min(13).max(150),
});

type CreateUserInput = z.infer<typeof createUserSchema>;

// Usage in Express
app.post('/api/users', (req, res) => {
  const result = createUserSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({ errors: result.error.flatten() });
  }
  const validData = result.data;
  // proceed with validated data
});
```

---

## 2. Output Encoding

**Principle**: Encode output according to the context where it will be rendered (HTML body, HTML attribute, JavaScript, URL, CSS).

### Context-Specific Encoding

| Context | Encoding | Example |
|---------|----------|---------|
| HTML body | HTML entity encode | `<` becomes `&lt;` |
| HTML attribute | HTML attribute encode | `"` becomes `&quot;` |
| JavaScript | JavaScript encode | `'` becomes `\x27` |
| URL parameter | URL encode | `&` becomes `%26` |
| CSS | CSS encode | `(` becomes `\28` |

### React (Built-in XSS Protection)

```tsx
// SAFE: React automatically escapes JSX expressions
function UserGreeting({ name }: { name: string }) {
  return <h1>Hello, {name}</h1>;  // name is HTML-escaped automatically
}

// DANGEROUS: Bypasses React's protection
function UnsafeContent({ html }: { html: string }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />;  // XSS risk
}

// SAFE: If you must render HTML, sanitize first
import DOMPurify from 'dompurify';

function SafeHtmlContent({ html }: { html: string }) {
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
    ALLOWED_ATTR: ['href', 'title'],
  });
  return <div dangerouslySetInnerHTML={{ __html: clean }} />;
}
```

### Python (Jinja2)

```python
# Jinja2 auto-escapes in HTML context by default
# {{ user_input }} is safe in templates

# For explicit encoding:
from markupsafe import escape

safe_output = escape(user_input)
```

---

## 3. Parameterized Queries

**Principle**: Never concatenate user input into SQL queries. Use parameterized queries or ORMs.

### Python (Various)

```python
# psycopg2 (PostgreSQL)
cursor.execute(
    "SELECT * FROM users WHERE email = %s AND status = %s",
    (email, 'active')
)

# SQLAlchemy ORM
user = session.query(User).filter(
    User.email == email,
    User.status == 'active'
).first()

# SQLAlchemy Core
from sqlalchemy import text
result = conn.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": email}
)

# Django ORM
user = User.objects.filter(email=email, status='active').first()

# Django raw query (parameterized)
User.objects.raw("SELECT * FROM auth_user WHERE email = %s", [email])
```

### JavaScript/TypeScript

```typescript
// Prisma (recommended)
const user = await prisma.user.findFirst({
  where: { email, status: 'active' },
});

// Knex.js
const user = await knex('users')
  .where({ email, status: 'active' })
  .first();

// pg (node-postgres) -- parameterized
const result = await pool.query(
  'SELECT * FROM users WHERE email = $1 AND status = $2',
  [email, 'active']
);

// mysql2 -- parameterized
const [rows] = await connection.execute(
  'SELECT * FROM users WHERE email = ? AND status = ?',
  [email, 'active']
);
```

---

## 4. Session Management

### Express.js

```typescript
import session from 'express-session';
import RedisStore from 'connect-redis';
import { createClient } from 'redis';

const redisClient = createClient({ url: process.env.REDIS_URL });
await redisClient.connect();

app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: process.env.SESSION_SECRET!,  // Strong random secret
  name: '__session',                     // Custom cookie name (not 'connect.sid')
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: true,        // HTTPS only
    httpOnly: true,      // Not accessible via JavaScript
    sameSite: 'strict',  // CSRF protection
    maxAge: 30 * 60 * 1000, // 30 minutes
    domain: '.example.com',
    path: '/',
  },
}));

// Regenerate session on login (prevent fixation)
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body);
  if (!user) return res.status(401).json({ error: 'Invalid credentials' });

  req.session.regenerate((err) => {
    if (err) return res.status(500).json({ error: 'Session error' });
    req.session.userId = user.id;
    req.session.save(() => {
      res.json({ success: true });
    });
  });
});

// Destroy session on logout
app.post('/logout', (req, res) => {
  req.session.destroy((err) => {
    res.clearCookie('__session');
    res.json({ success: true });
  });
});
```

### Flask

```python
from flask import Flask, session
from flask_session import Session
from datetime import timedelta

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ['SECRET_KEY'],
    SESSION_TYPE='redis',
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    SESSION_COOKIE_NAME='__session',
)
Session(app)
```

---

## 5. Password Hashing

**Never** use MD5, SHA1, SHA256, or any fast hash for passwords. Use bcrypt, argon2, or scrypt.

### Python

```python
# argon2 (recommended)
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,        # iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,
)

hashed = ph.hash("user_password")
# '$argon2id$v=19$m=65536,t=3,p=4$...'

try:
    ph.verify(hashed, "user_password")
    # Check if rehash needed (parameters changed)
    if ph.check_needs_rehash(hashed):
        new_hash = ph.hash("user_password")
        # Update stored hash
except argon2.exceptions.VerifyMismatchError:
    # Invalid password
    pass

# bcrypt (widely supported)
import bcrypt

hashed = bcrypt.hashpw(b"user_password", bcrypt.gensalt(rounds=12))
is_valid = bcrypt.checkpw(b"user_password", hashed)
```

### JavaScript/TypeScript

```typescript
// bcrypt
import bcrypt from 'bcrypt';

const SALT_ROUNDS = 12;

async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, SALT_ROUNDS);
}

async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

// argon2
import argon2 from 'argon2';

async function hashPassword(password: string): Promise<string> {
  return argon2.hash(password, {
    type: argon2.argon2id,
    memoryCost: 65536,  // 64 MB
    timeCost: 3,
    parallelism: 4,
  });
}

async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return argon2.verify(hash, password);
}
```

---

## 6. JWT Best Practices

### Token Creation

```typescript
import jwt from 'jsonwebtoken';

const ACCESS_TOKEN_SECRET = process.env.JWT_ACCESS_SECRET!;
const REFRESH_TOKEN_SECRET = process.env.JWT_REFRESH_SECRET!;

function createAccessToken(userId: string, roles: string[]): string {
  return jwt.sign(
    {
      sub: userId,
      roles,
      type: 'access',
    },
    ACCESS_TOKEN_SECRET,
    {
      algorithm: 'HS256',   // Or RS256 for asymmetric
      expiresIn: '15m',     // Short-lived
      issuer: 'myapp',
      audience: 'myapp-api',
    }
  );
}

function createRefreshToken(userId: string): string {
  return jwt.sign(
    { sub: userId, type: 'refresh' },
    REFRESH_TOKEN_SECRET,
    {
      algorithm: 'HS256',
      expiresIn: '7d',
      issuer: 'myapp',
    }
  );
}
```

### Token Verification

```typescript
function verifyAccessToken(token: string): JwtPayload {
  return jwt.verify(token, ACCESS_TOKEN_SECRET, {
    algorithms: ['HS256'],     // Explicitly specify allowed algorithms
    issuer: 'myapp',
    audience: 'myapp-api',
    complete: false,
  }) as JwtPayload;
}

// Middleware
function authMiddleware(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing token' });
  }

  const token = authHeader.slice(7);
  try {
    const payload = verifyAccessToken(token);
    req.user = { id: payload.sub, roles: payload.roles };
    next();
  } catch (err) {
    if (err instanceof jwt.TokenExpiredError) {
      return res.status(401).json({ error: 'Token expired' });
    }
    return res.status(401).json({ error: 'Invalid token' });
  }
}
```

### JWT Checklist

- [ ] Use `HS256` (symmetric) or `RS256` (asymmetric), never `none`
- [ ] Always specify `algorithms` in verify to prevent algorithm confusion
- [ ] Keep access tokens short-lived (5-15 minutes)
- [ ] Use refresh tokens (longer-lived) stored securely (httpOnly cookie)
- [ ] Include `iss`, `aud`, `exp`, `sub` claims
- [ ] Do not store sensitive data in JWT payload (it is base64-encoded, not encrypted)
- [ ] Implement token revocation for logout (blocklist or short expiry)
- [ ] Rotate signing keys periodically

---

## 7. CORS Configuration

### Express.js

```typescript
import cors from 'cors';

// PRODUCTION: Strict CORS
const corsOptions: cors.CorsOptions = {
  origin: ['https://app.example.com', 'https://admin.example.com'],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
  maxAge: 86400,  // Preflight cache: 24 hours
};

app.use(cors(corsOptions));

// NEVER do this in production:
// app.use(cors({ origin: '*', credentials: true }));
```

### Flask

```python
from flask_cors import CORS

CORS(app, resources={
    r'/api/*': {
        'origins': ['https://app.example.com'],
        'methods': ['GET', 'POST', 'PUT', 'DELETE'],
        'allow_headers': ['Content-Type', 'Authorization'],
        'supports_credentials': True,
        'max_age': 86400,
    }
})
```

### CORS Checklist

- [ ] Never use `origin: '*'` with `credentials: true`
- [ ] Specify exact allowed origins (no wildcards in production)
- [ ] Limit allowed methods to those actually needed
- [ ] Limit allowed headers to those actually used
- [ ] Set `maxAge` to reduce preflight requests
- [ ] Do not reflect the `Origin` header back dynamically without validation

---

## 8. Content Security Policy

### Recommended Policy

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self' https://api.example.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
  upgrade-insecure-requests;
```

### Express.js with Helmet

```typescript
import helmet from 'helmet';

app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'"],
    styleSrc: ["'self'", "'unsafe-inline'"],  // Required for many CSS-in-JS
    imgSrc: ["'self'", "data:", "https:"],
    fontSrc: ["'self'"],
    connectSrc: ["'self'", "https://api.example.com"],
    frameAncestors: ["'none'"],
    baseUri: ["'self'"],
    formAction: ["'self'"],
    upgradeInsecureRequests: [],
  },
}));

// Or use all Helmet defaults (recommended starting point)
app.use(helmet());
```

### CSP Checklist

- [ ] Avoid `unsafe-inline` for scripts (use nonces or hashes instead)
- [ ] Avoid `unsafe-eval` (breaks if using `eval()`, but that should be avoided anyway)
- [ ] Use `frame-ancestors 'none'` to prevent clickjacking (replaces X-Frame-Options)
- [ ] Use `upgrade-insecure-requests` to auto-upgrade HTTP to HTTPS
- [ ] Start with a strict policy, relax only as needed
- [ ] Use `Content-Security-Policy-Report-Only` header for testing
- [ ] Set up CSP violation reporting endpoint

---

## 9. Secure File Upload

### Express.js with Multer

```typescript
import multer from 'multer';
import path from 'path';
import crypto from 'crypto';

// Allowed MIME types (allowlist)
const ALLOWED_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'application/pdf',
]);

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB

const storage = multer.diskStorage({
  destination: './uploads/temp',
  filename: (req, file, cb) => {
    // Generate random filename to prevent path traversal and overwrites
    const randomName = crypto.randomBytes(16).toString('hex');
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, `${randomName}${ext}`);
  },
});

const upload = multer({
  storage,
  limits: {
    fileSize: MAX_FILE_SIZE,
    files: 1,  // Max number of files
  },
  fileFilter: (req, file, cb) => {
    // Validate MIME type
    if (!ALLOWED_TYPES.has(file.mimetype)) {
      return cb(new Error(`File type ${file.mimetype} not allowed`));
    }

    // Validate extension
    const ext = path.extname(file.originalname).toLowerCase();
    const allowedExtensions = new Set(['.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf']);
    if (!allowedExtensions.has(ext)) {
      return cb(new Error(`Extension ${ext} not allowed`));
    }

    cb(null, true);
  },
});

app.post('/api/upload', upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }

  // Additional validation: check file magic bytes
  const fileBuffer = await fs.readFile(req.file.path);
  const fileType = await import('file-type');
  const detected = await fileType.fileTypeFromBuffer(fileBuffer);

  if (!detected || !ALLOWED_TYPES.has(detected.mime)) {
    await fs.unlink(req.file.path);  // Delete suspicious file
    return res.status(400).json({ error: 'Invalid file content' });
  }

  // Move from temp to permanent storage
  // Serve from a separate domain or CDN (not the application domain)
  res.json({ filename: req.file.filename });
});
```

### File Upload Checklist

- [ ] Validate file type by MIME type AND magic bytes (not just extension)
- [ ] Use an allowlist of permitted file types
- [ ] Generate random filenames (never use user-provided names directly)
- [ ] Enforce maximum file size
- [ ] Store uploads outside the web root
- [ ] Serve uploaded files from a separate domain or CDN
- [ ] Scan uploaded files for malware
- [ ] Set `Content-Disposition: attachment` for downloads
- [ ] Do not execute uploaded files (no execute permissions on upload directory)
- [ ] Implement rate limiting on upload endpoints
