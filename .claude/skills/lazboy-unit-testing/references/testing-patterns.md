# Unit Testing Patterns

Comprehensive reference for writing effective unit tests with examples in Jest/Vitest and pytest.

---

## Table of Contents

1. [AAA Pattern (Arrange-Act-Assert)](#1-aaa-pattern)
2. [Test Doubles](#2-test-doubles)
3. [Test Data Builders and Factories](#3-test-data-builders-and-factories)
4. [Parameterized Tests](#4-parameterized-tests)
5. [Snapshot Testing](#5-snapshot-testing)
6. [Testing Async Code](#6-testing-async-code)
7. [Testing Error Paths](#7-testing-error-paths)
8. [Testing React Hooks](#8-testing-react-hooks)
9. [Integration vs. Unit Test Boundaries](#9-integration-vs-unit-test-boundaries)
10. [Anti-Patterns](#10-anti-patterns)

---

## 1. AAA Pattern

Every test should follow the Arrange-Act-Assert structure. One logical assertion per test.

### Jest/Vitest

```typescript
describe('calculateDiscount', () => {
  it('applies 10% discount for orders over $100', () => {
    // Arrange
    const order = { total: 150, items: 3 };

    // Act
    const result = calculateDiscount(order);

    // Assert
    expect(result).toBe(15);
  });

  it('returns zero discount for orders under $100', () => {
    // Arrange
    const order = { total: 50, items: 1 };

    // Act
    const result = calculateDiscount(order);

    // Assert
    expect(result).toBe(0);
  });
});
```

### pytest

```python
def test_calculate_discount_over_threshold():
    # Arrange
    order = Order(total=150, items=3)

    # Act
    result = calculate_discount(order)

    # Assert
    assert result == 15


def test_calculate_discount_under_threshold():
    # Arrange
    order = Order(total=50, items=1)

    # Act
    result = calculate_discount(order)

    # Assert
    assert result == 0
```

### Guidelines

- **One logical concept per test**: A test should verify one behavior. Multiple assertions are fine if they verify the same concept.
- **No logic in tests**: No if/else, loops, or try/catch in test code. If you need those, split into separate tests.
- **Descriptive test names**: The name should describe the scenario and expected outcome.

---

## 2. Test Doubles

### Types

| Type | Purpose | Records Calls? | Has Behavior? |
|------|---------|---------------|---------------|
| **Dummy** | Fill parameter lists | No | No |
| **Stub** | Provide canned answers | No | Yes (hardcoded) |
| **Spy** | Record interactions | Yes | Delegates to real impl |
| **Mock** | Verify interactions | Yes | Yes (programmed) |
| **Fake** | Simplified implementation | No | Yes (working but simple) |

### Jest/Vitest Examples

```typescript
// STUB: Returns a canned value
const userService = {
  getUser: jest.fn().mockResolvedValue({ id: 1, name: 'Alice' }),
};

// SPY: Wraps the real implementation
const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
// ... run code that should log errors ...
expect(spy).toHaveBeenCalledWith('Expected error message');
spy.mockRestore();

// MOCK: Full module mock
jest.mock('./emailService', () => ({
  sendEmail: jest.fn().mockResolvedValue({ success: true }),
}));

// FAKE: In-memory implementation
class FakeUserRepository {
  private users = new Map<string, User>();

  async save(user: User): Promise<void> {
    this.users.set(user.id, user);
  }

  async findById(id: string): Promise<User | null> {
    return this.users.get(id) ?? null;
  }

  async findAll(): Promise<User[]> {
    return Array.from(this.users.values());
  }
}
```

### pytest Examples

```python
from unittest.mock import MagicMock, patch, AsyncMock

# STUB with MagicMock
def test_process_order_with_stub():
    payment_gateway = MagicMock()
    payment_gateway.charge.return_value = {"status": "success", "tx_id": "abc123"}

    result = process_order(order, payment_gateway)
    assert result.status == "confirmed"


# SPY with wraps
def test_logging_with_spy():
    real_logger = Logger()
    spy_logger = MagicMock(wraps=real_logger)

    process_data(data, logger=spy_logger)
    spy_logger.info.assert_called_once_with("Processing complete")


# MOCK with patch
@patch("myapp.services.email_client")
def test_send_notification(mock_email):
    mock_email.send.return_value = True

    send_notification("user@example.com", "Hello")

    mock_email.send.assert_called_once_with(
        to="user@example.com",
        subject="Notification",
        body="Hello",
    )


# FAKE
class FakeCache:
    def __init__(self):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ttl=None):
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)
```

---

## 3. Test Data Builders and Factories

Avoid hardcoding test data. Use builders or factories for readable, maintainable test setups.

### Builder Pattern (TypeScript)

```typescript
class UserBuilder {
  private user: User = {
    id: 'user-1',
    name: 'Test User',
    email: 'test@example.com',
    role: 'user',
    active: true,
    createdAt: new Date('2024-01-01'),
  };

  withId(id: string): this {
    this.user.id = id;
    return this;
  }

  withName(name: string): this {
    this.user.name = name;
    return this;
  }

  withRole(role: 'user' | 'admin'): this {
    this.user.role = role;
    return this;
  }

  inactive(): this {
    this.user.active = false;
    return this;
  }

  build(): User {
    return { ...this.user };
  }
}

// Usage
const admin = new UserBuilder().withRole('admin').withName('Admin').build();
const inactiveUser = new UserBuilder().inactive().build();
```

### Factory Function (TypeScript)

```typescript
function createUser(overrides: Partial<User> = {}): User {
  return {
    id: `user-${Date.now()}`,
    name: 'Test User',
    email: 'test@example.com',
    role: 'user',
    active: true,
    createdAt: new Date(),
    ...overrides,
  };
}

// Usage
const admin = createUser({ role: 'admin', name: 'Admin' });
```

### Factory (Python)

```python
from dataclasses import dataclass, field
from datetime import datetime
import uuid


def create_user(**overrides) -> dict:
    defaults = {
        "id": str(uuid.uuid4()),
        "name": "Test User",
        "email": "test@example.com",
        "role": "user",
        "active": True,
        "created_at": datetime.utcnow(),
    }
    return {**defaults, **overrides}


# Usage
admin = create_user(role="admin", name="Admin User")
inactive = create_user(active=False)
```

---

## 4. Parameterized Tests

Test the same logic with multiple inputs without duplicating test code.

### Jest/Vitest

```typescript
describe('isValidEmail', () => {
  it.each([
    ['user@example.com', true],
    ['user@sub.example.com', true],
    ['user+tag@example.com', true],
    ['invalid', false],
    ['@example.com', false],
    ['user@', false],
    ['', false],
  ])('validates "%s" as %s', (email, expected) => {
    expect(isValidEmail(email)).toBe(expected);
  });
});

// With named parameters
describe('calculateShipping', () => {
  it.each`
    weight | distance | expected
    ${1}   | ${10}    | ${5.0}
    ${5}   | ${10}    | ${12.5}
    ${1}   | ${100}   | ${15.0}
    ${10}  | ${500}   | ${75.0}
  `(
    'charges $expected for ${weight}kg over ${distance}km',
    ({ weight, distance, expected }) => {
      expect(calculateShipping(weight, distance)).toBe(expected);
    }
  );
});
```

### pytest

```python
import pytest


@pytest.mark.parametrize(
    "email, expected",
    [
        ("user@example.com", True),
        ("user@sub.example.com", True),
        ("user+tag@example.com", True),
        ("invalid", False),
        ("@example.com", False),
        ("user@", False),
        ("", False),
    ],
)
def test_is_valid_email(email, expected):
    assert is_valid_email(email) == expected


@pytest.mark.parametrize(
    "weight, distance, expected",
    [
        (1, 10, 5.0),
        (5, 10, 12.5),
        (1, 100, 15.0),
        (10, 500, 75.0),
    ],
    ids=["light-short", "medium-short", "light-long", "heavy-long"],
)
def test_calculate_shipping(weight, distance, expected):
    assert calculate_shipping(weight, distance) == expected
```

---

## 5. Snapshot Testing

Capture output and compare against a saved snapshot. Good for serializable outputs like rendered components, API responses, or configuration objects.

### Jest/Vitest

```typescript
// Component snapshot
it('renders correctly', () => {
  const tree = render(<UserCard user={mockUser} />);
  expect(tree.container).toMatchSnapshot();
});

// Inline snapshot (stored in the test file itself)
it('formats user display name', () => {
  expect(formatDisplayName({ first: 'John', last: 'Doe' }))
    .toMatchInlineSnapshot(`"Doe, John"`);
});

// Custom serializer for complex objects
expect.addSnapshotSerializer({
  test: (val) => val instanceof Date,
  print: (val) => `Date(${(val as Date).toISOString()})`,
});
```

### pytest (with syrupy or snapshot)

```python
# Using syrupy
def test_api_response(snapshot):
    response = get_user_response(user_id="123")
    assert response == snapshot


def test_config_generation(snapshot):
    config = generate_config(env="production")
    assert config == snapshot
```

### When to Use Snapshots

- **Good for**: Rendered HTML/JSX, API response shapes, configuration output, error messages
- **Bad for**: Large objects with volatile fields (timestamps, IDs), testing logic (use assertions instead)
- **Guideline**: If you would not notice a meaningful change in a snapshot diff during code review, do not use snapshots

---

## 6. Testing Async Code

### Jest/Vitest

```typescript
// async/await
it('fetches user data', async () => {
  const user = await fetchUser('123');
  expect(user.name).toBe('Alice');
});

// Promises
it('fetches user data', () => {
  return fetchUser('123').then((user) => {
    expect(user.name).toBe('Alice');
  });
});

// Testing rejected promises
it('throws for invalid user', async () => {
  await expect(fetchUser('invalid')).rejects.toThrow('User not found');
});

// Fake timers
it('retries after delay', async () => {
  jest.useFakeTimers();
  const promise = retryOperation(failingFn);
  jest.advanceTimersByTime(3000);
  await expect(promise).resolves.toBe('success');
  jest.useRealTimers();
});
```

### pytest

```python
import pytest
import asyncio


@pytest.mark.asyncio
async def test_fetch_user():
    user = await fetch_user("123")
    assert user.name == "Alice"


@pytest.mark.asyncio
async def test_fetch_user_not_found():
    with pytest.raises(UserNotFoundError):
        await fetch_user("invalid")


# Testing with event loop
@pytest.mark.asyncio
async def test_concurrent_requests():
    results = await asyncio.gather(
        fetch_user("1"),
        fetch_user("2"),
        fetch_user("3"),
    )
    assert len(results) == 3
```

---

## 7. Testing Error Paths

Test that your code handles errors correctly. Error path tests are as important as happy path tests.

### Jest/Vitest

```typescript
describe('createOrder', () => {
  it('throws InsufficientStockError when product is out of stock', async () => {
    const product = createProduct({ stock: 0 });
    await expect(createOrder(product, 1)).rejects.toThrow(InsufficientStockError);
  });

  it('throws ValidationError for negative quantity', async () => {
    const product = createProduct({ stock: 10 });
    await expect(createOrder(product, -1)).rejects.toThrow('Quantity must be positive');
  });

  it('rolls back on payment failure', async () => {
    paymentGateway.charge.mockRejectedValue(new PaymentError('Declined'));
    const inventoryBefore = await getInventory(product.id);

    await expect(createOrder(product, 1)).rejects.toThrow(PaymentError);

    const inventoryAfter = await getInventory(product.id);
    expect(inventoryAfter).toBe(inventoryBefore); // No inventory deducted
  });
});
```

### pytest

```python
import pytest


def test_create_order_out_of_stock():
    product = create_product(stock=0)
    with pytest.raises(InsufficientStockError):
        create_order(product, quantity=1)


def test_create_order_negative_quantity():
    product = create_product(stock=10)
    with pytest.raises(ValidationError, match="Quantity must be positive"):
        create_order(product, quantity=-1)


def test_create_order_payment_failure_rollback(mock_payment_gateway):
    mock_payment_gateway.charge.side_effect = PaymentError("Declined")
    product = create_product(stock=10)
    inventory_before = get_inventory(product.id)

    with pytest.raises(PaymentError):
        create_order(product, quantity=1)

    assert get_inventory(product.id) == inventory_before
```

---

## 8. Testing React Hooks

### Using renderHook (Testing Library)

```typescript
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

describe('useCounter', () => {
  it('starts with initial value', () => {
    const { result } = renderHook(() => useCounter(10));
    expect(result.current.count).toBe(10);
  });

  it('increments the counter', () => {
    const { result } = renderHook(() => useCounter(0));

    act(() => {
      result.current.increment();
    });

    expect(result.current.count).toBe(1);
  });

  it('resets to initial value', () => {
    const { result } = renderHook(() => useCounter(5));

    act(() => {
      result.current.increment();
      result.current.increment();
    });
    expect(result.current.count).toBe(7);

    act(() => {
      result.current.reset();
    });
    expect(result.current.count).toBe(5);
  });
});

// Hook with dependencies
describe('useDebounce', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it('debounces value updates', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    expect(result.current).toBe('initial');

    rerender({ value: 'updated' });
    expect(result.current).toBe('initial'); // Not yet updated

    act(() => jest.advanceTimersByTime(500));
    expect(result.current).toBe('updated'); // Now updated
  });
});

// Hook with context
describe('useAuth', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  it('returns current user', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(false);
  });
});
```

---

## 9. Integration vs. Unit Test Boundaries

### Unit Tests

Test a single unit (function, class, component) in isolation.

| Test | What to Mock | What to Keep Real |
|------|-------------|-------------------|
| Pure function | Nothing | Everything |
| Service with DB | Database calls | Business logic |
| API handler | Service layer | Request parsing, validation |
| React component | API calls, context | Component rendering, user events |

### Integration Tests

Test multiple units working together with real (or close-to-real) dependencies.

| Test | What to Mock | What to Keep Real |
|------|-------------|-------------------|
| API endpoint | External services | Router + handler + service + validation |
| Database operations | Nothing | ORM + database (test DB) |
| Service flow | External APIs | Service + repository + domain logic |

### The Testing Trophy

```
           /\
          /  \     E2E (few)
         /----\
        /      \   Integration (some)
       /--------\
      /          \  Unit (many)
     /------------\
    / Static Types \ (most)
```

Invest most in static types and unit tests. Integration tests cover the gaps. E2E tests validate critical user flows.

---

## 10. Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| **Testing implementation** | Breaks on refactor | Test behavior/output, not internal state |
| **Overuse of mocks** | Tests pass but code is broken | Mock only boundaries (I/O, external services) |
| **Shared mutable state** | Order-dependent, flaky | Fresh setup per test (beforeEach) |
| **Testing framework code** | Low value | Trust the framework; test YOUR code |
| **God test** | One test does everything | Split into focused tests |
| **Invisible assertion** | No expect/assert | Every test needs at least one assertion |
| **Magic numbers** | Unclear why values are chosen | Use named constants or builder patterns |
| **Conditional test logic** | Hard to understand | Split into separate tests |
| **Sleeping in tests** | Slow, flaky | Use fake timers or await specific conditions |
| **Ignoring test failures** | Tech debt | Fix or delete; never skip permanently |
