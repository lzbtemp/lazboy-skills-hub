# Code Review Checklist

Comprehensive review checklist for La-Z-Boy engineering teams. Work through each section in priority order. Not every item applies to every PR — use judgment based on the scope of changes.

---

## 1. Security

### Authentication & Authorization
- [ ] All new endpoints enforce authentication
- [ ] Role-based access control is correctly applied
- [ ] JWT tokens are validated on the server side, not just the client
- [ ] Session management follows secure practices (HttpOnly, Secure, SameSite cookies)
- [ ] No authorization bypass through parameter tampering or IDOR vulnerabilities

### Input Validation & Injection
- [ ] All user input is validated on the server side (never trust client validation alone)
- [ ] SQL queries use parameterized statements or ORM methods — no string concatenation
- [ ] GraphQL queries have depth and complexity limits
- [ ] File uploads validate type, size, and content (not just extension)
- [ ] No use of `eval()`, `exec()`, `Function()`, or `dangerouslySetInnerHTML` with user data
- [ ] URL redirects are validated against an allowlist

### Secrets & Sensitive Data
- [ ] No hardcoded API keys, passwords, tokens, or connection strings
- [ ] Secrets are loaded from environment variables or a secrets manager
- [ ] Sensitive data is not logged (PII, credentials, tokens)
- [ ] `.env` files and credential files are in `.gitignore`
- [ ] Error responses do not leak stack traces or internal details to clients

### Dependencies
- [ ] New dependencies are from reputable, actively maintained sources
- [ ] `npm audit` / `pip audit` / `safety check` shows no critical vulnerabilities
- [ ] Lock files (`package-lock.json`, `poetry.lock`) are committed
- [ ] No unnecessary dependencies added (check if native/stdlib alternatives exist)

---

## 2. Correctness

### Logic
- [ ] Business logic matches the acceptance criteria / ticket requirements
- [ ] Edge cases are handled (empty inputs, null values, boundary conditions)
- [ ] Off-by-one errors are absent in loops and slices
- [ ] Numeric operations handle overflow, underflow, and division by zero
- [ ] Boolean conditions are correct (no accidental `&&` vs `||` swaps)

### Error Handling
- [ ] Errors are caught at appropriate levels (not swallowed silently)
- [ ] Error messages are actionable for the caller
- [ ] Async operations have proper error handling (`.catch()`, `try/except`)
- [ ] Network failures, timeouts, and retries are handled gracefully
- [ ] Transactions are rolled back on failure

### Concurrency & State
- [ ] Race conditions are addressed in shared state scenarios
- [ ] Database operations use appropriate isolation levels
- [ ] Optimistic concurrency or locking is used where needed
- [ ] State mutations are atomic where required
- [ ] Event ordering assumptions are documented and validated

### Data Integrity
- [ ] Database migrations are reversible
- [ ] Schema changes are backward-compatible with running application instances
- [ ] Data type conversions are explicit and safe
- [ ] Timezone handling is consistent (store in UTC, convert at display)

---

## 3. Performance

### Database
- [ ] No N+1 query patterns (use eager loading / `select_related` / `JOIN`)
- [ ] Queries use appropriate indexes (check `EXPLAIN` for new queries)
- [ ] Bulk operations are used instead of loops for batch inserts/updates
- [ ] Pagination is implemented for list endpoints (cursor-based preferred)
- [ ] Connection pooling is configured correctly

### Caching
- [ ] Frequently accessed, rarely changed data is cached
- [ ] Cache invalidation strategy is correct and documented
- [ ] Cache keys are namespaced to avoid collisions
- [ ] TTLs are appropriate for the data freshness requirements

### Network & I/O
- [ ] API responses are appropriately sized (no over-fetching)
- [ ] Large payloads use compression (gzip/brotli)
- [ ] File operations use streaming for large files
- [ ] Async operations are parallelized where independent (`Promise.all`, `asyncio.gather`)

---

## 4. Frontend (React / TypeScript)

### Rendering
- [ ] `useEffect` dependency arrays are complete and correct
- [ ] Expensive computations are wrapped in `useMemo` / `useCallback` where beneficial
- [ ] Lists render with stable, unique `key` props (not array index for dynamic lists)
- [ ] Large lists use virtualization (`react-window`, `react-virtuoso`)
- [ ] Components do not re-render unnecessarily (verify with React DevTools profiler)

### State Management
- [ ] State is stored at the correct level (local vs. global)
- [ ] Derived state is computed, not stored separately
- [ ] Form state uses controlled components or a form library consistently
- [ ] Server state uses a data-fetching library (React Query, SWR) with proper cache config
- [ ] No prop drilling beyond 2 levels — use context or composition

### TypeScript
- [ ] No `any` types (use `unknown` if the type is truly not known)
- [ ] Interfaces/types are defined for all props, API responses, and domain objects
- [ ] Discriminated unions are used for variant types
- [ ] Generics are used where they reduce duplication
- [ ] Strict null checks are satisfied (no non-null assertions `!` without justification)

### Accessibility
- [ ] Interactive elements are keyboard accessible
- [ ] ARIA labels are present on non-text interactive elements
- [ ] Color is not the sole means of conveying information
- [ ] Focus management is correct for modals, drawers, and dynamic content
- [ ] Heading hierarchy is logical (`h1` > `h2` > `h3`)

### Styling & Layout
- [ ] Responsive design works at mobile, tablet, and desktop breakpoints
- [ ] No hardcoded pixel values for spacing (use design tokens / theme)
- [ ] CSS-in-JS / Tailwind classes follow project conventions
- [ ] No CSS specificity wars or `!important` overrides
- [ ] Dark mode / theme support is maintained if applicable

---

## 5. Backend (Python / Node.js)

### Python-Specific
- [ ] Type hints are present on all function signatures
- [ ] Docstrings follow the project convention (Google, NumPy, or Sphinx style)
- [ ] Context managers are used for resource cleanup (`with` statements)
- [ ] List comprehensions are preferred over `map`/`filter` for simple transformations
- [ ] `pathlib.Path` is used instead of `os.path` string manipulation
- [ ] No mutable default arguments (`def func(items=[])` is a bug)
- [ ] F-strings are used for string formatting (not `%` or `.format()`)
- [ ] Imports follow isort ordering: stdlib, third-party, local

### Node.js-Specific
- [ ] Async functions use `async/await` consistently (no mixing callbacks and promises)
- [ ] Event emitters have error handlers attached
- [ ] Streams are properly destroyed / closed on error
- [ ] No synchronous file I/O in request handlers
- [ ] Environment-specific config is not hardcoded (use `dotenv` or config service)
- [ ] Express middleware is ordered correctly (auth before route handlers)

### API Design
- [ ] RESTful conventions are followed (correct HTTP methods and status codes)
- [ ] Request/response schemas are validated (Pydantic, Zod, Joi)
- [ ] API versioning strategy is consistent
- [ ] Rate limiting is applied to public endpoints
- [ ] CORS configuration is restrictive (not `*` in production)
- [ ] Idempotency is supported for mutating operations where appropriate

---

## 6. Testing

### Coverage & Quality
- [ ] New code has accompanying unit tests
- [ ] Critical paths have integration tests
- [ ] Tests assert behavior, not implementation details
- [ ] Edge cases and error paths are tested
- [ ] Test names clearly describe the scenario and expected outcome

### Test Practices
- [ ] Tests are independent and can run in any order
- [ ] Test data is created in the test (not dependent on shared fixtures that mutate)
- [ ] External dependencies are mocked at the boundary (API calls, databases)
- [ ] Snapshot tests are used sparingly and snapshots are reviewed when updated
- [ ] No test code in production bundles

### Frontend Testing
- [ ] Components are tested with React Testing Library (not Enzyme)
- [ ] User interactions are tested (`userEvent` over `fireEvent`)
- [ ] Accessibility assertions are included (`toBeVisible`, `toHaveAccessibleName`)
- [ ] Loading, error, and empty states are tested
- [ ] Custom hooks are tested with `renderHook`

### Backend Testing
- [ ] API endpoints have request/response contract tests
- [ ] Database queries are tested against a test database (not mocked)
- [ ] Background jobs and workers have tests
- [ ] Authentication and authorization are tested (positive and negative cases)

---

## 7. Maintainability

### Naming & Readability
- [ ] Variable, function, and class names are descriptive and consistent
- [ ] Abbreviations are avoided unless universally understood (`id`, `url`, `config`)
- [ ] Boolean variables/functions use `is`, `has`, `should`, `can` prefixes
- [ ] Constants are UPPER_SNAKE_CASE and grouped logically
- [ ] No magic numbers — use named constants with explanatory names

### Structure
- [ ] Functions do one thing (single responsibility)
- [ ] Cyclomatic complexity is under 10 per function
- [ ] Files are under 300 lines (consider splitting if larger)
- [ ] Nesting depth is under 4 levels (use early returns, guard clauses)
- [ ] Dead code is removed, not commented out

### Documentation
- [ ] Public APIs have JSDoc / docstring documentation
- [ ] Complex algorithms have explanatory comments (the "why", not the "what")
- [ ] README or docs are updated if behavior or setup changes
- [ ] Architecture Decision Records (ADRs) are created for significant design choices
- [ ] TODO comments include a ticket number or owner

---

## 8. Style & Conventions

_These should be automated via linters and formatters. Only flag manually if tooling is not configured._

- [ ] Code passes all lint checks (ESLint, Pylint, Ruff)
- [ ] Code is formatted by the project formatter (Prettier, Black)
- [ ] Import ordering follows project convention
- [ ] File naming follows project convention (kebab-case, PascalCase, etc.)
- [ ] Commit messages follow conventional commits format

---

## Quick Reference: Review Decision Matrix

| Finding | Severity | Action |
|---|---|---|
| SQL injection, XSS, hardcoded secrets | Critical | Block PR, fix immediately |
| Missing auth checks, data loss risk | High | Block PR |
| N+1 queries, missing error handling | Medium | Request changes |
| Missing tests for new code | Medium | Request changes |
| Unclear naming, minor style issues | Low | Suggest, approve anyway |
| Formatting, import order | Info | Comment or auto-fix |
