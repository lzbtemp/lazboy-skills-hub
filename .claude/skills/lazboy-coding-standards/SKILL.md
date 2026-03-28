---
name: lazboy-coding-standards
description: "Enforce coding standards and best practices across TypeScript, JavaScript, and React projects. Use this skill whenever writing new code, reviewing PRs, or refactoring existing code. Triggers on: code quality, naming conventions, file organization, API design, performance optimization, or testing standards."
version: "1.0.0"
category: Code Quality
tags: [typescript, javascript, react, standards, best-practices]
---

# Coding Standards & Best Practices

Consistent, readable, maintainable code across all projects.

## 1. Code Quality Principles

- **Readability First**: Code is read more than written — optimize for clarity
- **KISS**: Choose the simplest solution that works
- **DRY**: Extract common logic into reusable functions
- **YAGNI**: Don't build features before they're needed

## 2. TypeScript/JavaScript Standards

### Naming Conventions

- **Variables**: Descriptive camelCase — `marketSearchQuery`, `isUserAuthenticated`, `totalRevenue`
- **Functions**: Verb-noun pattern — `fetchMarketData()`, `calculateSimilarity()`, `isValidEmail()`
- **Constants**: UPPER_SNAKE_CASE — `MAX_RETRIES`, `DEBOUNCE_DELAY_MS`
- **Components**: PascalCase — `UserProfile`, `SearchResults`

### Immutability

Always use spread operator for object/array updates:

```typescript
// ✅ Correct
const updated = { ...user, name: newName };
const newItems = [...items, newItem];

// ❌ Wrong
user.name = newName;
items.push(newItem);
```

### Error Handling

```typescript
// ✅ Comprehensive try-catch with meaningful messages
try {
  const data = await fetchMarketData(query);
  return processResults(data);
} catch (error) {
  logger.error('Failed to fetch market data', { query, error });
  throw new AppError('Market data unavailable', { cause: error });
}
```

### Async/Await

Use `Promise.all()` for parallel execution when operations are independent:

```typescript
// ✅ Parallel — independent operations
const [users, products, orders] = await Promise.all([
  fetchUsers(),
  fetchProducts(),
  fetchOrders(),
]);

// ❌ Sequential — unnecessary wait
const users = await fetchUsers();
const products = await fetchProducts();
const orders = await fetchOrders();
```

### Type Safety

- Avoid `any` type — use proper interfaces and union types
- Define explicit return types for public functions
- Use discriminated unions for state management

```typescript
// ✅ Type-safe response
interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  meta?: { total: number; page: number };
}
```

## 3. React Best Practices

### Component Structure

```typescript
// ✅ Functional component with typed props
interface UserCardProps {
  user: User;
  onSelect: (id: string) => void;
  isActive?: boolean;
}

export function UserCard({ user, onSelect, isActive = false }: UserCardProps) {
  // hooks first
  const [isExpanded, setIsExpanded] = useState(false);

  // handlers
  const handleClick = useCallback(() => {
    onSelect(user.id);
  }, [user.id, onSelect]);

  // render
  return (
    <div className={isActive ? 'active' : ''} onClick={handleClick}>
      {user.name}
    </div>
  );
}
```

### Custom Hooks

Create reusable hooks for shared logic:

```typescript
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
```

### State Management

Use functional updates with setState:

```typescript
// ✅ Functional update — always uses latest state
setItems(prev => [...prev, newItem]);

// ❌ Stale closure risk
setItems([...items, newItem]);
```

## 4. API Design Standards

### REST Conventions

| Method | URL Pattern | Purpose |
|--------|-------------|---------|
| GET | `/api/users` | List resources |
| GET | `/api/users/:id` | Get single resource |
| POST | `/api/users` | Create resource |
| PUT | `/api/users/:id` | Full update |
| PATCH | `/api/users/:id` | Partial update |
| DELETE | `/api/users/:id` | Remove resource |

### Response Format

```typescript
interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  meta?: {
    total: number;
    page: number;
    limit: number;
  };
}
```

### Input Validation

Use Zod for schema validation:

```typescript
const createUserSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email(),
  role: z.enum(['admin', 'user', 'viewer']),
});
```

## 5. File Organization

```
src/
├── app/              # Routes and pages
├── components/       # Reusable UI components
│   ├── ui/           # Primitives (Button, Input)
│   └── features/     # Feature-specific components
├── hooks/            # Custom React hooks
├── lib/              # Utilities and helpers
├── types/            # TypeScript type definitions
└── styles/           # Global styles
```

- **PascalCase** for component files: `UserCard.tsx`
- **camelCase** for utilities and hooks: `useDebounce.ts`, `formatDate.ts`

## 6. Comments & Documentation

- Explain **WHY**, not **WHAT** — avoid stating the obvious
- Use JSDoc for public APIs:

```typescript
/**
 * Calculates similarity score between two text embeddings.
 *
 * @param a - First embedding vector
 * @param b - Second embedding vector
 * @returns Cosine similarity score between 0 and 1
 * @throws {Error} When vectors have different dimensions
 */
function cosineSimilarity(a: number[], b: number[]): number {
  // ...
}
```

## 7. Performance Optimization

- **Memoization**: `useMemo` for expensive computations, `useCallback` for stable references
- **Lazy loading**: `React.lazy()` with `Suspense` boundaries for code splitting
- **Database**: Select only needed columns — avoid `SELECT *`
- **Lists**: Virtualize long lists with `@tanstack/react-virtual`

## 8. Testing Standards

Follow AAA pattern — Arrange, Act, Assert:

```typescript
it('should calculate total price with discount', () => {
  // Arrange
  const items = [{ price: 100 }, { price: 200 }];
  const discount = 0.1;

  // Act
  const total = calculateTotal(items, discount);

  // Assert
  expect(total).toBe(270);
});
```

- Descriptive test names explaining expected behavior
- Focus on meaningful coverage, not 100% line coverage

## 9. Code Smells to Avoid

| Smell | Fix |
|-------|-----|
| Long functions (>50 lines) | Split into smaller, focused functions |
| Deep nesting (5+ levels) | Use early returns |
| Magic numbers | Named constants: `MAX_RETRIES`, `DEBOUNCE_DELAY_MS` |
| Boolean parameters | Use options object or separate functions |
| God objects | Single Responsibility — split by concern |
