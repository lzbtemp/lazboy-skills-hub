---
name: lazboy-security-review
description: >
  Comprehensive security review checklist for web applications. Use this skill
  whenever implementing authentication, handling user input, creating API endpoints,
  working with secrets, implementing payments, storing sensitive data, or integrating
  third-party APIs. Trigger on: security audit, vulnerability check, pre-deployment
  review, or any code that touches auth, input validation, or data exposure.
version: "1.0.0"
category: Security
tags: [security, authentication, authorization, xss, csrf, owasp]
---

# Security Review Checklist

Comprehensive security checklist covering 10 core domains with code examples and verification steps.

## 1. Secrets Management

Never hardcode credentials. Use environment variables exclusively.

```typescript
// ❌ NEVER do this
const API_KEY = "sk-1234567890abcdef";

// ✅ Always use environment variables
const API_KEY = process.env.API_KEY;
if (!API_KEY) throw new Error("API_KEY not configured");
```

- Store secrets in `.env` files (never committed to git)
- Use a secrets manager (AWS Secrets Manager, Vault) in production
- Rotate keys on a regular schedule

## 2. Input Validation

Validate all user input with schemas. Never trust client-side data.

```typescript
import { z } from 'zod';

const userInputSchema = z.object({
  email: z.string().email().max(255),
  name: z.string().min(1).max(100).trim(),
  age: z.number().int().min(0).max(150),
  file: z.object({
    size: z.number().max(5 * 1024 * 1024), // 5MB max
    type: z.enum(['image/png', 'image/jpeg', 'application/pdf']),
  }).optional(),
});

// Validate before processing
const result = userInputSchema.safeParse(req.body);
if (!result.success) {
  return res.status(400).json({ errors: result.error.flatten() });
}
```

## 3. SQL Injection Prevention

Always use parameterized queries. Never concatenate strings into SQL.

```typescript
// ❌ SQL Injection vulnerability
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// ✅ Parameterized query
const { data } = await supabase
  .from('users')
  .select('*')
  .eq('id', userId);

// ✅ Raw SQL with parameters
const result = await db.query('SELECT * FROM users WHERE id = $1', [userId]);
```

## 4. Authentication & Authorization

### Cookie Security

```typescript
// ✅ Secure cookie settings
res.cookie('session', token, {
  httpOnly: true,      // Prevent XSS access
  secure: true,        // HTTPS only
  sameSite: 'strict',  // Prevent CSRF
  maxAge: 3600000,     // 1 hour
  path: '/',
});
```

### Role-Based Access Control

```typescript
// ✅ Check permissions before acting
async function deleteUser(requesterId: string, targetId: string) {
  const requester = await getUser(requesterId);
  if (requester.role !== 'admin') {
    throw new ForbiddenError('Only admins can delete users');
  }
  await db.users.delete(targetId);
}
```

### Row-Level Security

```sql
-- ✅ Users can only see their own data
CREATE POLICY "users_own_data" ON documents
  FOR SELECT USING (auth.uid() = user_id);
```

## 5. XSS Prevention

Sanitize all HTML output. Use Content Security Policy headers.

```typescript
import DOMPurify from 'dompurify';

// ✅ Sanitize before rendering user content
const clean = DOMPurify.sanitize(userHtml, {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p'],
  ALLOWED_ATTR: ['href', 'title'],
});
```

```typescript
// ✅ CSP headers
app.use((req, res, next) => {
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
  );
  next();
});
```

## 6. CSRF Protection

```typescript
import csrf from 'csurf';

// ✅ CSRF middleware
app.use(csrf({ cookie: { sameSite: 'strict', httpOnly: true } }));

// Include token in forms
app.get('/form', (req, res) => {
  res.render('form', { csrfToken: req.csrfToken() });
});
```

## 7. Rate Limiting

```typescript
import rateLimit from 'express-rate-limit';

// ✅ General API rate limit
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  message: { error: 'Too many requests, try again later' },
});

// ✅ Stricter limit for auth endpoints
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  message: { error: 'Too many login attempts' },
});

app.use('/api/', apiLimiter);
app.use('/api/auth/', authLimiter);
```

## 8. Sensitive Data Exposure

```typescript
// ✅ Redact sensitive data in logs
function sanitizeForLog(obj: Record<string, any>) {
  const sensitive = ['password', 'token', 'secret', 'apiKey', 'ssn'];
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) =>
      sensitive.some(s => k.toLowerCase().includes(s))
        ? [k, '[REDACTED]']
        : [k, v]
    )
  );
}

// ✅ Generic error messages to users
catch (error) {
  logger.error('Database error', { error, userId });
  res.status(500).json({ error: 'Something went wrong' }); // No details
}
```

## 9. Dependency Security

- Run `npm audit` regularly and fix critical vulnerabilities
- Keep `package-lock.json` committed and up to date
- Enable Dependabot or Renovate for automated updates
- Review new dependencies before adding them

```bash
# ✅ Regular security audit
npm audit --production
npm audit fix
```

## 10. Pre-Deployment Checklist

- [ ] All secrets are in environment variables (not in code)
- [ ] Input validation on all user-facing endpoints
- [ ] Parameterized queries — no string concatenation in SQL
- [ ] Authentication on all protected routes
- [ ] Authorization checks at the data layer
- [ ] HttpOnly, Secure, SameSite cookies
- [ ] CSP and security headers configured
- [ ] Rate limiting on API and auth endpoints
- [ ] CORS restricted to known origins
- [ ] HTTPS enforced in production
- [ ] Error messages don't expose internals
- [ ] Sensitive data redacted from logs
- [ ] Dependencies audited for vulnerabilities
- [ ] File uploads validated (type, size, name)
- [ ] API keys have minimum required permissions
- [ ] Database backups configured and tested

## 11. Automated Security Tests

```typescript
describe('Security', () => {
  it('should reject unauthenticated requests', async () => {
    const res = await request(app).get('/api/users');
    expect(res.status).toBe(401);
  });

  it('should reject unauthorized access', async () => {
    const res = await request(app)
      .delete('/api/users/123')
      .set('Authorization', `Bearer ${userToken}`); // non-admin
    expect(res.status).toBe(403);
  });

  it('should reject invalid input', async () => {
    const res = await request(app)
      .post('/api/users')
      .send({ email: 'not-an-email', name: '' });
    expect(res.status).toBe(400);
  });

  it('should enforce rate limits', async () => {
    for (let i = 0; i < 6; i++) {
      await request(app).post('/api/auth/login').send({ email: 'test@test.com', password: 'wrong' });
    }
    const res = await request(app).post('/api/auth/login').send({ email: 'test@test.com', password: 'wrong' });
    expect(res.status).toBe(429);
  });
});
```
