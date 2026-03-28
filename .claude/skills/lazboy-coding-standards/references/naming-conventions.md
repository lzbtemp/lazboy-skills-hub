# Naming Conventions for TypeScript, JavaScript, and React

Comprehensive naming guide covering variables, functions, classes, interfaces, types,
constants, file names, and test files. Every section includes good and bad examples.

---

## 1. General Principles

- Names should reveal intent -- a reader should understand the purpose without comments
- Avoid abbreviations unless universally understood (e.g., `id`, `url`, `api`)
- Longer scopes warrant longer, more descriptive names
- Shorter scopes (loop variables, lambdas) can use shorter names
- Be consistent within a codebase -- pick one convention and stick with it

---

## 2. Variables

**Convention:** `camelCase`

Use descriptive nouns. Boolean variables should read as yes/no questions.

### Good Examples

```typescript
const userProfile = await fetchUser(id);
const totalRevenue = orders.reduce((sum, o) => sum + o.amount, 0);
const marketSearchQuery = params.get('q');
const activeSubscriptions = subscriptions.filter(s => s.isActive);

// Booleans — prefix with is, has, can, should, was
const isAuthenticated = !!session?.user;
const hasPermission = user.permissions.includes('write');
const canEdit = isAuthenticated && hasPermission;
const shouldRefresh = lastFetched < Date.now() - STALE_THRESHOLD;
const wasDeleted = response.status === 204;
```

### Bad Examples

```typescript
// Too vague
const data = await fetchUser(id);      // What data?
const temp = orders.filter(o => o.active); // Temp what?
const val = params.get('q');           // Val of what?
const flag = !!session?.user;          // Which flag?

// Misleading
const userList = fetchUser(id);        // Returns one user, not a list
const isData = response.data;          // Not a boolean

// Unnecessary abbreviation
const usrProf = await fetchUser(id);
const actSubs = subscriptions.filter(s => s.isActive);
const mktSrchQry = params.get('q');
```

---

## 3. Functions and Methods

**Convention:** `camelCase` with verb-noun pattern

The function name should describe what it does. Use a verb prefix that communicates
the operation type.

### Verb Prefix Guide

| Prefix     | Usage                        | Example                       |
|------------|------------------------------|-------------------------------|
| `get`      | Return a value (sync)        | `getUser()`, `getTotal()`     |
| `fetch`    | Retrieve from external source| `fetchMarketData()`           |
| `create`   | Make something new           | `createOrder()`               |
| `update`   | Modify existing              | `updateProfile()`             |
| `delete`   | Remove something             | `deleteComment()`             |
| `is/has`   | Return boolean               | `isValid()`, `hasAccess()`    |
| `calculate`| Compute a value              | `calculateDiscount()`         |
| `format`   | Transform for display        | `formatCurrency()`            |
| `validate` | Check input validity         | `validateEmail()`             |
| `parse`    | Extract structured data      | `parseQueryString()`          |
| `handle`   | Event handler                | `handleSubmit()`              |
| `on`       | Event callback (React)       | `onSelect()`, `onClick()`     |
| `render`   | Produce UI output            | `renderUserCard()`            |
| `transform`| Convert from one shape to another | `transformApiResponse()` |

### Good Examples

```typescript
function fetchMarketData(query: string): Promise<MarketData[]> { /* ... */ }
function calculateSimilarityScore(a: number[], b: number[]): number { /* ... */ }
function isValidEmail(email: string): boolean { /* ... */ }
function formatCurrency(amount: number, currency: string): string { /* ... */ }
function parseQueryParams(url: string): Record<string, string> { /* ... */ }
function handleFormSubmit(event: FormEvent): void { /* ... */ }
```

### Bad Examples

```typescript
// No verb — what does this do?
function userData(id: string) { /* ... */ }
function email(input: string) { /* ... */ }

// Verb does not match behavior
function getUsers() { /* actually creates users */ }

// Too generic
function process(data: any) { /* ... */ }
function doStuff() { /* ... */ }
function handle(e: any) { /* ... */ }

// Redundant type in name
function getUserObject(id: string) { /* ... */ }   // Just getUser
function fetchDataArray(query: string) { /* ... */ } // Just fetchData
```

---

## 4. React Components

**Convention:** `PascalCase`

Components are nouns describing what they render. They do not use verb prefixes.

### Good Examples

```typescript
export function UserProfile({ userId }: { userId: string }) { /* ... */ }
export function SearchResultCard({ result }: SearchResultCardProps) { /* ... */ }
export function NavigationSidebar() { /* ... */ }
export function OrderSummaryTable({ orders }: OrderSummaryTableProps) { /* ... */ }
export function ConfirmDeleteDialog({ onConfirm, onCancel }: DialogProps) { /* ... */ }
```

### Bad Examples

```typescript
// camelCase — wrong for components
export function userProfile() { /* ... */ }

// Verb prefix — components are nouns
export function renderUserProfile() { /* ... */ }
export function displaySearchResults() { /* ... */ }

// Too generic
export function Card() { /* ... */ }    // Card of what?
export function List() { /* ... */ }    // List of what?
export function Modal() { /* ... */ }   // Modal for what?

// Abbreviations
export function UsrProf() { /* ... */ }
export function SrchRes() { /* ... */ }
```

---

## 5. React Props Interfaces

**Convention:** `PascalCase` with `Props` suffix

### Good Examples

```typescript
interface UserCardProps {
  user: User;
  onSelect: (userId: string) => void;
  isActive?: boolean;
}

interface SearchBarProps {
  initialQuery?: string;
  onSearch: (query: string) => void;
  placeholder?: string;
  isLoading?: boolean;
}

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}
```

### Bad Examples

```typescript
// Missing Props suffix
interface UserCard {
  user: User;
}

// I- prefix (Hungarian notation — avoid in TypeScript)
interface IUserCardProps {
  user: User;
}

// Generic name
interface Props {
  data: any;
}
```

---

## 6. Interfaces and Types

**Convention:** `PascalCase`, descriptive nouns

### Interfaces

Use interfaces for object shapes, especially when they may be extended.

```typescript
// Good — clear domain objects
interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  createdAt: Date;
}

interface CreateUserInput {
  name: string;
  email: string;
  role: UserRole;
}

interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  meta?: PaginationMeta;
}

interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}
```

### Type Aliases

Use type aliases for unions, intersections, mapped types, and primitives.

```typescript
// Good
type UserRole = 'admin' | 'editor' | 'viewer';
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
type AsyncResult<T> = { data: T; error: null } | { data: null; error: AppError };
type DeepPartial<T> = { [P in keyof T]?: DeepPartial<T[P]> };
type UserId = string; // Branded type for clarity
```

```typescript
// Bad — avoid I- prefix and unclear names
type IUser = { /* ... */ };
type Data = any;
type Obj = Record<string, unknown>;
type Callback = Function;  // Use specific function signature instead
```

---

## 7. Constants

**Convention:** `UPPER_SNAKE_CASE` for true constants (values known at compile time)

### Good Examples

```typescript
// Configuration constants
const MAX_RETRIES = 3;
const DEBOUNCE_DELAY_MS = 300;
const DEFAULT_PAGE_SIZE = 20;
const API_BASE_URL = 'https://api.example.com/v1';
const CACHE_TTL_SECONDS = 300;

// Enum-like constant objects (use as const)
const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  NOT_FOUND: 404,
  INTERNAL_ERROR: 500,
} as const;

const USER_ROLES = {
  ADMIN: 'admin',
  EDITOR: 'editor',
  VIEWER: 'viewer',
} as const;
```

### Bad Examples

```typescript
// Not using UPPER_SNAKE_CASE for true constants
const maxRetries = 3;              // Looks like a regular variable
const debounceDelay = 300;

// Using UPPER_SNAKE_CASE for derived/computed values
const FILTERED_USERS = users.filter(u => u.active);  // Not a constant
const USER_COUNT = users.length;                      // Not a constant

// Magic numbers without named constants
setTimeout(callback, 300);         // Use DEBOUNCE_DELAY_MS
if (retries > 3) throw error;     // Use MAX_RETRIES
```

---

## 8. Enums

**Convention:** `PascalCase` for the enum, `PascalCase` for members

Prefer string unions over TypeScript enums for better tree-shaking.
When you must use enums, use PascalCase members.

```typescript
// Preferred: string union type
type OrderStatus = 'Pending' | 'Processing' | 'Shipped' | 'Delivered' | 'Cancelled';

// If you must use an enum
enum LogLevel {
  Debug = 'DEBUG',
  Info = 'INFO',
  Warn = 'WARN',
  Error = 'ERROR',
}
```

---

## 9. Custom React Hooks

**Convention:** `camelCase` with `use` prefix

```typescript
// Good
function useDebounce<T>(value: T, delay: number): T { /* ... */ }
function useLocalStorage<T>(key: string, initialValue: T): [T, (v: T) => void] { /* ... */ }
function useMediaQuery(query: string): boolean { /* ... */ }
function useClickOutside(ref: RefObject<HTMLElement>, handler: () => void): void { /* ... */ }
function useIntersectionObserver(options: IntersectionOptions): IntersectionResult { /* ... */ }

// Bad — missing use prefix
function debounce<T>(value: T, delay: number): T { /* ... */ }      // Not a hook name
function localStorageHelper(key: string): unknown { /* ... */ }       // Not a hook name
```

---

## 10. File Names

### Components (PascalCase)

```
components/
  UserProfile.tsx
  SearchResultCard.tsx
  NavigationSidebar.tsx
  ConfirmDeleteDialog.tsx
  ui/
    Button.tsx
    Input.tsx
    Select.tsx
```

### Utilities and Hooks (camelCase)

```
hooks/
  useDebounce.ts
  useLocalStorage.ts
  useMediaQuery.ts

lib/
  formatCurrency.ts
  validateEmail.ts
  parseQueryString.ts
```

### Configuration and Constants (camelCase or kebab-case)

```
config/
  database.ts
  redis.ts

constants/
  httpStatus.ts
  userRoles.ts
```

### Backend Layers (camelCase with suffix)

```
controllers/
  userController.ts
  orderController.ts

services/
  userService.ts
  orderService.ts

repositories/
  userRepository.ts
  orderRepository.ts
```

### Bad File Names

```
// Inconsistent casing
components/
  user-profile.tsx      // Should be PascalCase for components
  Searchresultcard.tsx  // Missing capital C in Card

// Ambiguous names
utils.ts               // Too generic — what utils?
helpers.ts             // Too generic — what helpers?
data.ts                // Data of what?
```

---

## 11. Test Files

**Convention:** Same name as the module with `.test.ts` or `.spec.ts` suffix.
Place test files next to the source file or in a `__tests__` directory.

### File Naming

```
// Co-located tests (preferred)
services/
  userService.ts
  userService.test.ts

components/
  UserProfile.tsx
  UserProfile.test.tsx

// Or __tests__ directory
services/
  __tests__/
    userService.test.ts
  userService.ts
```

### Test Description Naming

```typescript
// Good — describe blocks match the unit, it blocks describe behavior
describe('UserService', () => {
  describe('createUser', () => {
    it('should create a user with valid input', () => { /* ... */ });
    it('should throw ConflictError when email already exists', () => { /* ... */ });
    it('should normalize email to lowercase', () => { /* ... */ });
  });

  describe('getUser', () => {
    it('should return the user when found', () => { /* ... */ });
    it('should throw NotFoundError when user does not exist', () => { /* ... */ });
  });
});
```

```typescript
// Bad — vague test names
describe('tests', () => {
  it('works', () => { /* ... */ });
  it('test 1', () => { /* ... */ });
  it('should do stuff correctly', () => { /* ... */ });
  it('handles errors', () => { /* ... */ });  // Which errors?
});
```

---

## 12. Event Handlers and Callbacks

**Convention:** `handle` prefix for component handlers, `on` prefix for props

```typescript
// In the component that defines the handler
function UserForm() {
  const handleSubmit = (e: FormEvent) => { /* ... */ };
  const handleNameChange = (e: ChangeEvent<HTMLInputElement>) => { /* ... */ };
  const handleDelete = () => { /* ... */ };

  return (
    <form onSubmit={handleSubmit}>
      <input onChange={handleNameChange} />
      <DeleteButton onDelete={handleDelete} />
    </form>
  );
}

// In the component that accepts the handler as a prop
interface DeleteButtonProps {
  onDelete: () => void;      // "on" prefix for callback props
  onConfirm?: () => void;
}
```

---

## 13. Quick Reference Table

| Entity                 | Convention         | Example                          |
|------------------------|--------------------|----------------------------------|
| Variable               | camelCase          | `userProfile`, `totalCount`      |
| Boolean variable       | camelCase + is/has | `isActive`, `hasPermission`      |
| Function               | camelCase + verb   | `fetchData()`, `calculateTotal()`|
| React component        | PascalCase         | `UserProfile`, `SearchBar`       |
| Props interface        | PascalCase + Props | `UserCardProps`                  |
| Interface              | PascalCase         | `User`, `ApiResponse`            |
| Type alias             | PascalCase         | `UserRole`, `HttpMethod`         |
| Constant               | UPPER_SNAKE_CASE   | `MAX_RETRIES`, `API_BASE_URL`    |
| Enum                   | PascalCase         | `LogLevel`, `OrderStatus`        |
| Custom hook            | camelCase + use    | `useDebounce`, `useAuth`         |
| Component file         | PascalCase.tsx     | `UserProfile.tsx`                |
| Utility file           | camelCase.ts       | `formatCurrency.ts`              |
| Test file              | *.test.ts          | `userService.test.ts`            |
| Event handler          | handleX            | `handleSubmit`, `handleClick`    |
| Callback prop          | onX                | `onSelect`, `onChange`           |
| CSS class (Tailwind)   | kebab-case         | `user-profile`, `nav-sidebar`    |
| Environment variable   | UPPER_SNAKE_CASE   | `DATABASE_URL`, `JWT_SECRET`     |
| URL route segment      | kebab-case         | `/api/user-profiles`             |

---

*Reference for lazboy-coding-standards skill v1.0.0*
