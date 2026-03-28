# Code Quality & PR Review Checklist

Comprehensive checklist for pull request reviews covering naming, complexity, DRY
principle, error handling, testing, documentation, performance, and security.

Use this checklist during code reviews to ensure consistent quality across the codebase.

---

## How to Use This Checklist

Each section contains specific items to verify. Mark each item as:
- **PASS** -- meets the standard
- **WARN** -- minor issue, consider fixing
- **FAIL** -- must fix before merge

Priority levels:
- **P0 (Critical)** -- blocks merge: security vulnerabilities, data loss risks, broken functionality
- **P1 (High)** -- should fix before merge: bugs, missing error handling, test gaps
- **P2 (Medium)** -- fix soon: naming issues, minor code smells, documentation gaps
- **P3 (Low)** -- nice to have: style preferences, minor optimizations

---

## 1. Naming and Readability (P2)

### Variables and Functions

- [ ] Variables use descriptive `camelCase` names that reveal intent
- [ ] Boolean variables use `is`, `has`, `can`, `should`, or `was` prefix
- [ ] Functions use verb-noun pattern (`fetchUser`, `calculateTotal`, `isValid`)
- [ ] No single-letter variable names outside of short lambdas and loop indices
- [ ] No abbreviations unless universally understood (`id`, `url`, `api`)
- [ ] No misleading names (e.g., `userList` for a single user)

### Components and Types

- [ ] React components use `PascalCase`
- [ ] Props interfaces use `PascalCase` with `Props` suffix
- [ ] Interfaces and types use `PascalCase` nouns
- [ ] Constants use `UPPER_SNAKE_CASE`
- [ ] Custom hooks start with `use` prefix

### Files

- [ ] Component files use `PascalCase.tsx`
- [ ] Utility and hook files use `camelCase.ts`
- [ ] Test files use `*.test.ts` or `*.spec.ts` suffix
- [ ] File name matches the primary export

---

## 2. Code Complexity (P1)

### Function Complexity

- [ ] No function exceeds 50 lines (excluding comments and blank lines)
- [ ] Cyclomatic complexity per function is 10 or less
- [ ] No more than 3 levels of nesting (use early returns to flatten)
- [ ] Functions have 4 or fewer parameters (use an options object for more)
- [ ] Each function has a single, clear responsibility

### File Complexity

- [ ] No file exceeds 300 lines (excluding imports and comments)
- [ ] Each file has a single, clear purpose
- [ ] No god objects or god modules that do everything

### Conditional Logic

- [ ] Complex conditions are extracted into well-named boolean variables or functions
- [ ] No nested ternaries
- [ ] Switch/case statements have a default branch
- [ ] Early returns are used to avoid deep nesting

```typescript
// BAD — deep nesting
function processOrder(order: Order) {
  if (order) {
    if (order.items.length > 0) {
      if (order.status === 'pending') {
        // actual logic buried 3 levels deep
      }
    }
  }
}

// GOOD — early returns
function processOrder(order: Order) {
  if (!order) return;
  if (order.items.length === 0) return;
  if (order.status !== 'pending') return;

  // actual logic at top level
}
```

---

## 3. DRY Principle (P2)

### Code Duplication

- [ ] No copy-pasted blocks of 5+ lines (extract into shared functions)
- [ ] Similar components use a shared base or composition pattern
- [ ] Common API call patterns use a shared utility (e.g., `apiClient`)
- [ ] Validation logic is shared via Zod schemas, not duplicated

### Abstraction Quality

- [ ] Shared utilities are genuinely reusable, not forced abstractions
- [ ] Abstractions have 3+ callers (avoid premature abstraction)
- [ ] Helper functions are placed in the correct location (local, module, or shared)
- [ ] No "utility dump" files with unrelated functions

```typescript
// BAD — premature abstraction with only 1 caller
function buildUserGreeting(user: User): string {
  return `Hello, ${user.name}`;
}

// GOOD — inline simple one-off logic
const greeting = `Hello, ${user.name}`;

// GOOD — extract when there are 3+ callers or complex logic
function formatCurrency(amount: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
}
```

---

## 4. Error Handling (P1)

### Try/Catch Usage

- [ ] All async operations are wrapped in try/catch or use `.catch()`
- [ ] Catch blocks do not silently swallow errors (`catch (e) {}`)
- [ ] Error messages are descriptive and actionable
- [ ] Errors include relevant context (user ID, request path, input data)
- [ ] Re-thrown errors preserve the original error as `cause`

### Error Types

- [ ] Custom error classes are used for different error categories
- [ ] HTTP status codes match the error type (404 for not found, 409 for conflict)
- [ ] Validation errors return 400 with field-level details
- [ ] Internal errors do not expose stack traces or implementation details to clients

### Edge Cases

- [ ] Null/undefined values are handled explicitly
- [ ] Empty arrays and empty strings are handled
- [ ] Network timeouts have reasonable limits and fallbacks
- [ ] Race conditions in async code are considered

```typescript
// BAD — silent error swallowing
try {
  await saveData(input);
} catch (e) {
  // nothing
}

// BAD — generic error, no context
try {
  await saveData(input);
} catch (e) {
  throw new Error('Something went wrong');
}

// GOOD — specific error with context
try {
  await saveData(input);
} catch (error) {
  logger.error('Failed to save user data', { userId: input.id, error });
  throw new AppError('Unable to save user data', { cause: error });
}
```

---

## 5. Testing (P1)

### Test Coverage

- [ ] New features have corresponding tests
- [ ] Bug fixes include a regression test
- [ ] Happy path is tested
- [ ] Error paths are tested (invalid input, missing data, network failures)
- [ ] Edge cases are tested (empty arrays, null values, boundary values)

### Test Quality

- [ ] Tests follow AAA pattern (Arrange, Act, Assert)
- [ ] Test names describe expected behavior, not implementation
- [ ] Each test verifies one thing (single assertion concept)
- [ ] Tests do not depend on execution order
- [ ] Tests do not share mutable state
- [ ] No hardcoded test data that could become stale (dates, IDs)

### Mocking

- [ ] External dependencies (APIs, databases) are mocked
- [ ] Mocks are minimal -- only mock what you must
- [ ] Mock implementations match the real interface
- [ ] No over-mocking that makes tests meaningless

```typescript
// BAD — vague test name, no AAA structure
it('works', () => {
  expect(calculateTotal([{ price: 10 }], 0.1)).toBe(9);
});

// GOOD — clear name, AAA structure
it('should apply percentage discount to the sum of item prices', () => {
  // Arrange
  const items = [{ price: 100 }, { price: 200 }];
  const discountRate = 0.1;

  // Act
  const total = calculateTotal(items, discountRate);

  // Assert
  expect(total).toBe(270);
});
```

---

## 6. Documentation (P3)

### Code Comments

- [ ] Comments explain **why**, not **what**
- [ ] No commented-out code (use version control instead)
- [ ] Complex algorithms have a brief explanation
- [ ] TODOs include a ticket reference or owner

### Public API Documentation

- [ ] Exported functions have JSDoc with `@param` and `@returns`
- [ ] Complex types have doc comments explaining their purpose
- [ ] API endpoints document request/response shapes

### Self-Documenting Code

- [ ] Code is clear enough that most comments are unnecessary
- [ ] Function and variable names make the logic readable
- [ ] Complex logic is extracted into well-named helper functions

```typescript
// BAD — comment states the obvious
// Get the user
const user = await getUser(id);

// BAD — commented-out code
// const oldLogic = calculateLegacy(data);
const result = calculateNew(data);

// GOOD — comment explains WHY
// Cache user for 10 min because profile rarely changes and
// the /dashboard endpoint calls this 3x per render
const user = await cache.getOrFetch(`user:${id}`, () => getUser(id), 600);
```

---

## 7. Performance (P2)

### React Performance

- [ ] `useMemo` is used for expensive calculations (not for simple lookups)
- [ ] `useCallback` is used for callbacks passed to memoized children
- [ ] Large lists use virtualization (`@tanstack/react-virtual`)
- [ ] Images use lazy loading and appropriate sizes
- [ ] No unnecessary re-renders from object/array literals in JSX props

### Data Fetching

- [ ] Only needed columns are selected from the database (no `SELECT *`)
- [ ] N+1 query patterns are avoided (use batch fetching)
- [ ] Pagination is implemented for list endpoints
- [ ] Appropriate cache headers are set for API responses

### Bundle Size

- [ ] Large libraries are imported selectively, not entirely
- [ ] Dynamic imports (`React.lazy`) used for route-level code splitting
- [ ] No duplicate dependencies in the bundle
- [ ] Dev-only dependencies are not in production bundle

```typescript
// BAD — imports entire library
import _ from 'lodash';
const sorted = _.sortBy(items, 'name');

// GOOD — import only what you need
import sortBy from 'lodash/sortBy';
const sorted = sortBy(items, 'name');

// BETTER — use native method
const sorted = [...items].sort((a, b) => a.name.localeCompare(b.name));
```

---

## 8. Security (P0)

### Input Validation

- [ ] All user input is validated on the server side
- [ ] Input is validated using a schema library (Zod, Joi) not manual checks
- [ ] File uploads validate type, size, and content
- [ ] URL parameters and query strings are sanitized

### Authentication and Authorization

- [ ] Protected routes check authentication
- [ ] Authorization checks verify the user can access the specific resource
- [ ] Tokens are validated on every request, not just at login
- [ ] Password/secret values are never logged

### Data Protection

- [ ] No secrets in source code (use environment variables)
- [ ] `.env` files are in `.gitignore`
- [ ] Sensitive data is not included in API responses (passwords, tokens)
- [ ] SQL/NoSQL injection is prevented (parameterized queries)
- [ ] XSS is prevented (user input is escaped before rendering)

### HTTP Security

- [ ] CORS is configured to allow only trusted origins
- [ ] Rate limiting is applied to authentication endpoints
- [ ] Security headers are set (`X-Content-Type-Options`, `X-Frame-Options`, etc.)
- [ ] HTTPS is enforced in production

```typescript
// BAD — SQL injection risk
const query = `SELECT * FROM users WHERE email = '${input.email}'`;

// GOOD — parameterized query
const { data } = await db
  .from('users')
  .select('id, name, email')
  .eq('email', input.email);

// BAD — exposing sensitive data
res.json({ user: { ...user, passwordHash: user.passwordHash } });

// GOOD — select only safe fields
res.json({ user: { id: user.id, name: user.name, email: user.email } });
```

---

## 9. TypeScript Specific (P2)

### Type Safety

- [ ] No `any` type usage (use `unknown`, generics, or proper interfaces)
- [ ] Function return types are explicit for public/exported functions
- [ ] Discriminated unions are used for state management
- [ ] Type assertions (`as`) are justified and commented when used
- [ ] `strictNullChecks` is enabled

### Immutability

- [ ] Objects are updated with spread operator, not mutation
- [ ] Arrays are updated with `map`/`filter`/`concat`, not `push`/`splice`
- [ ] `const` is used by default; `let` only when reassignment is needed
- [ ] `readonly` is used for properties that should not change

---

## 10. Architecture (P2)

### Layered Architecture

- [ ] Controllers handle only HTTP request/response (no business logic)
- [ ] Services contain business logic and orchestration
- [ ] Repositories abstract data access
- [ ] No circular dependencies between layers

### Component Architecture (React)

- [ ] Components have a single responsibility
- [ ] Shared state is managed through context or a state management library
- [ ] Side effects are isolated in custom hooks
- [ ] Props drilling does not exceed 2 levels (use context beyond that)

### Module Organization

- [ ] Related code is co-located (feature-based organization)
- [ ] Shared code is in a clearly designated shared/lib directory
- [ ] Imports are ordered: external, internal, relative
- [ ] No circular imports

---

## PR Review Summary Template

```
## Review Summary

**PR:** #123 — Add user profile editing
**Reviewer:** @reviewer
**Verdict:** APPROVE / REQUEST CHANGES / COMMENT

### Findings

| # | Category     | Severity | File               | Description                          |
|---|-------------|----------|--------------------|--------------------------------------|
| 1 | Security    | P0       | userController.ts  | Missing auth check on PATCH endpoint |
| 2 | Error       | P1       | userService.ts     | Silent catch on line 45              |
| 3 | Naming      | P2       | helpers.ts         | Function `proc` — unclear purpose    |
| 4 | Performance | P3       | UserList.tsx       | Could benefit from virtualization    |

### What Went Well
- Clean separation of concerns in the service layer
- Comprehensive test coverage for edge cases
- Good use of TypeScript discriminated unions for form state

### Suggestions
- Consider extracting the validation logic into a shared schema
- The `formatAddress` function is duplicated in 2 components
```

---

*Reference for lazboy-coding-standards skill v1.0.0*
