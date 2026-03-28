# Mocking Best Practices Guide

When, what, and how to mock in unit tests -- with patterns for Jest, pytest, and HTTP mocking.

---

## Table of Contents

1. [When to Mock](#1-when-to-mock)
2. [When NOT to Mock](#2-when-not-to-mock)
3. [Jest Mock Patterns](#3-jest-mock-patterns)
4. [pytest Mock Patterns](#4-pytest-mock-patterns)
5. [Mocking HTTP Calls](#5-mocking-http-calls)
6. [Test Database Patterns](#6-test-database-patterns)
7. [Guidelines](#7-guidelines)

---

## 1. When to Mock

Mock these dependencies because they are slow, non-deterministic, or have side effects.

### External APIs and Services

```typescript
// Mock external payment service
jest.mock('./services/stripe', () => ({
  chargeCard: jest.fn().mockResolvedValue({ id: 'ch_123', status: 'succeeded' }),
}));

test('processes payment', async () => {
  const result = await checkout(order);
  expect(result.paymentId).toBe('ch_123');
  expect(stripe.chargeCard).toHaveBeenCalledWith({
    amount: order.total,
    currency: 'usd',
  });
});
```

### Databases

```python
@patch("myapp.repositories.user_repo.find_by_id")
def test_get_user_profile(mock_find):
    mock_find.return_value = User(id="123", name="Alice")
    profile = get_user_profile("123")
    assert profile.name == "Alice"
    mock_find.assert_called_once_with("123")
```

### Time and Dates

```typescript
// Jest fake timers
beforeEach(() => jest.useFakeTimers());
afterEach(() => jest.useRealTimers());

test('token expires after 1 hour', () => {
  jest.setSystemTime(new Date('2024-01-01T12:00:00Z'));
  const token = createToken();

  jest.setSystemTime(new Date('2024-01-01T12:30:00Z'));
  expect(isTokenValid(token)).toBe(true);

  jest.setSystemTime(new Date('2024-01-01T13:01:00Z'));
  expect(isTokenValid(token)).toBe(false);
});
```

```python
from freezegun import freeze_time

@freeze_time("2024-01-01 12:00:00")
def test_token_expiry():
    token = create_token()
    assert is_token_valid(token) is True

@freeze_time("2024-01-01 13:01:00")
def test_token_expired():
    with freeze_time("2024-01-01 12:00:00"):
        token = create_token()
    assert is_token_valid(token) is False
```

### Randomness

```typescript
test('generates predictable IDs in test', () => {
  jest.spyOn(Math, 'random').mockReturnValue(0.5);
  const id = generateId();
  expect(id).toBe('expected-value');
});
```

```python
def test_generate_code(monkeypatch):
    monkeypatch.setattr("random.randint", lambda a, b: 42)
    code = generate_verification_code()
    assert code == "424242"
```

### File System

```typescript
jest.mock('fs/promises', () => ({
  readFile: jest.fn().mockResolvedValue('file contents'),
  writeFile: jest.fn().mockResolvedValue(undefined),
}));
```

### Environment Variables

```python
def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    config = load_config()
    assert config.database_url == "postgres://localhost/test"
```

---

## 2. When NOT to Mock

### Pure Functions

Pure functions have no side effects and always return the same output for the same input. Test them directly.

```typescript
// DON'T mock the internals of pure functions
// BAD:
jest.mock('./math', () => ({ add: jest.fn().mockReturnValue(5) }));

// GOOD: Just test the function
test('adds two numbers', () => {
  expect(add(2, 3)).toBe(5);
});
```

### Value Objects and Data Structures

```typescript
// DON'T mock data objects
// BAD:
const mockUser = { getName: jest.fn().mockReturnValue('Alice') };

// GOOD: Use real objects
const user = new User('Alice', 'alice@example.com');
expect(user.getName()).toBe('Alice');
```

### Simple Internal Collaborators

If a class depends on simple, fast, deterministic collaborators, use the real implementation.

```python
# DON'T mock simple formatters/validators
# BAD:
@patch("myapp.validators.validate_email")
def test_register(mock_validate):
    mock_validate.return_value = True
    # This test proves nothing about validation

# GOOD: Use real validator
def test_register_with_valid_email():
    result = register("alice@example.com", "password123")
    assert result.success is True

def test_register_with_invalid_email():
    with pytest.raises(ValidationError):
        register("not-an-email", "password123")
```

### The Code Under Test Itself

Never mock the thing you are testing.

---

## 3. Jest Mock Patterns

### jest.fn() -- Create a Mock Function

```typescript
// Basic mock
const callback = jest.fn();
processItems([1, 2, 3], callback);
expect(callback).toHaveBeenCalledTimes(3);
expect(callback).toHaveBeenCalledWith(1);

// Mock with return value
const getPrice = jest.fn().mockReturnValue(9.99);
const getPriceAsync = jest.fn().mockResolvedValue(9.99);

// Mock with implementation
const calculate = jest.fn().mockImplementation((a, b) => a + b);

// Mock different return values per call
const fetch = jest.fn()
  .mockResolvedValueOnce({ status: 'pending' })
  .mockResolvedValueOnce({ status: 'complete' });
```

### jest.mock() -- Mock a Module

```typescript
// Auto-mock entire module
jest.mock('./database');

// Mock with custom implementation
jest.mock('./emailService', () => ({
  sendEmail: jest.fn().mockResolvedValue(true),
  getTemplate: jest.fn().mockReturnValue('<html>{{body}}</html>'),
}));

// Partial mock (keep some real implementations)
jest.mock('./utils', () => ({
  ...jest.requireActual('./utils'),
  fetchData: jest.fn(),  // Only mock fetchData
}));

// Mock ES module default export
jest.mock('./config', () => ({
  __esModule: true,
  default: { apiUrl: 'http://test-api', debug: false },
}));
```

### jest.spyOn() -- Spy on Existing Methods

```typescript
// Spy on a method (tracks calls but runs real implementation)
const spy = jest.spyOn(userService, 'getUser');
await processUser('123');
expect(spy).toHaveBeenCalledWith('123');

// Spy and replace implementation
jest.spyOn(console, 'error').mockImplementation(() => {});

// Spy on a class prototype
jest.spyOn(Date.prototype, 'toISOString').mockReturnValue('2024-01-01T00:00:00.000Z');

// IMPORTANT: Restore spies after test
afterEach(() => {
  jest.restoreAllMocks();
});
```

### Mock Assertions

```typescript
const fn = jest.fn();

// Call count
expect(fn).toHaveBeenCalled();
expect(fn).toHaveBeenCalledTimes(3);
expect(fn).not.toHaveBeenCalled();

// Call arguments
expect(fn).toHaveBeenCalledWith('arg1', 'arg2');
expect(fn).toHaveBeenLastCalledWith('final-arg');
expect(fn).toHaveBeenNthCalledWith(1, 'first-call-arg');

// Partial matching
expect(fn).toHaveBeenCalledWith(
  expect.objectContaining({ id: '123' })
);
expect(fn).toHaveBeenCalledWith(
  expect.stringContaining('error')
);

// Access raw call data
expect(fn.mock.calls[0][0]).toBe('first-arg-of-first-call');
expect(fn.mock.results[0].value).toBe('return-value');
```

---

## 4. pytest Mock Patterns

### monkeypatch (Built-in Fixture)

```python
# Replace an attribute
def test_with_monkeypatch(monkeypatch):
    monkeypatch.setattr("myapp.config.API_URL", "http://test")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.delenv("PRODUCTION", raising=False)
    monkeypatch.setattr(requests, "get", lambda url: MockResponse(200, {}))
```

### MagicMock

```python
from unittest.mock import MagicMock, AsyncMock, PropertyMock, call

# Basic mock
service = MagicMock()
service.get_user.return_value = {"id": "123", "name": "Alice"}

# Async mock
async_service = AsyncMock()
async_service.fetch_data.return_value = {"key": "value"}

# Side effects (sequential returns)
mock_db = MagicMock()
mock_db.query.side_effect = [
    [{"id": 1}],     # First call returns this
    [{"id": 2}],     # Second call returns this
    Exception("DB error"),  # Third call raises
]

# Property mock
type(mock_obj).name = PropertyMock(return_value="test-name")

# Call assertions
service.get_user.assert_called_once_with("123")
service.get_user.assert_called_with("123")  # Last call only
service.get_user.assert_not_called()
service.get_user.assert_has_calls([
    call("123"),
    call("456"),
], any_order=True)
```

### patch Decorator and Context Manager

```python
from unittest.mock import patch

# Decorator
@patch("myapp.services.user_service.send_email")
@patch("myapp.services.user_service.save_to_db")
def test_register_user(mock_save, mock_email):  # Note: reverse order
    mock_save.return_value = {"id": "123"}
    mock_email.return_value = True

    result = register_user("alice@example.com")
    assert result["id"] == "123"


# Context manager
def test_with_context_manager():
    with patch("myapp.services.get_config") as mock_config:
        mock_config.return_value = {"feature_flag": True}
        result = process()
        assert result.feature_enabled is True


# patch.object (patch a method on a specific object)
def test_with_patch_object():
    with patch.object(UserService, "validate", return_value=True):
        service = UserService()
        assert service.validate("test@example.com") is True


# patch.dict (patch a dictionary)
@patch.dict(os.environ, {"API_KEY": "test-key"}, clear=False)
def test_reads_api_key():
    assert get_api_key() == "test-key"
```

### Fixtures

```python
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.connect.return_value = True
    db.query.return_value = []
    return db


@pytest.fixture
def mock_email_service():
    service = MagicMock()
    service.send.return_value = {"message_id": "msg-123"}
    return service


def test_process_order(mock_db, mock_email_service):
    processor = OrderProcessor(db=mock_db, email=mock_email_service)
    result = processor.process(order)

    mock_db.query.assert_called_once()
    mock_email_service.send.assert_called_once()
```

---

## 5. Mocking HTTP Calls

### MSW (Mock Service Worker) -- JavaScript

The recommended approach for mocking HTTP in tests. Intercepts requests at the network level.

```typescript
// mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'Alice',
      email: 'alice@example.com',
    });
  }),

  http.post('/api/users', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(
      { id: 'new-123', ...body },
      { status: 201 }
    );
  }),

  http.get('/api/users', () => {
    return HttpResponse.json([
      { id: '1', name: 'Alice' },
      { id: '2', name: 'Bob' },
    ]);
  }),
];

// mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

// setupTests.ts (or vitest.setup.ts)
import { server } from './mocks/server';

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// In tests: override handlers per test
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';

test('handles server error', async () => {
  server.use(
    http.get('/api/users/:id', () => {
      return new HttpResponse(null, { status: 500 });
    })
  );

  await expect(fetchUser('123')).rejects.toThrow('Server error');
});
```

### responses -- Python

```python
import responses
import requests

@responses.activate
def test_fetch_user():
    responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": "123", "name": "Alice"},
        status=200,
    )

    result = fetch_user("123")
    assert result["name"] == "Alice"
    assert len(responses.calls) == 1


@responses.activate
def test_api_error():
    responses.add(
        responses.GET,
        "https://api.example.com/users/999",
        json={"error": "Not found"},
        status=404,
    )

    with pytest.raises(UserNotFoundError):
        fetch_user("999")
```

### httpx with respx -- Python (async)

```python
import respx
import httpx

@respx.mock
async def test_async_fetch():
    respx.get("https://api.example.com/data").mock(
        return_value=httpx.Response(200, json={"key": "value"})
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        assert response.json() == {"key": "value"}
```

---

## 6. Test Database Patterns

### In-Memory Database (SQLite)

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_user(db_session):
    user = User(name="Alice", email="alice@example.com")
    db_session.add(user)
    db_session.commit()

    result = db_session.query(User).filter_by(email="alice@example.com").first()
    assert result.name == "Alice"
```

### Transaction Rollback (PostgreSQL)

```python
@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()  # Rollback -- no data persists
    connection.close()
```

### Prisma (TypeScript)

```typescript
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

beforeEach(async () => {
  // Clean tables before each test
  await prisma.$transaction([
    prisma.order.deleteMany(),
    prisma.user.deleteMany(),
  ]);
});

afterAll(async () => {
  await prisma.$disconnect();
});

test('creates a user', async () => {
  const user = await prisma.user.create({
    data: { name: 'Alice', email: 'alice@test.com' },
  });
  expect(user.id).toBeDefined();
  expect(user.name).toBe('Alice');
});
```

---

## 7. Guidelines

### The Mock Spectrum

```
No mocks                                    Everything mocked
    |<-- Integration tests -->|<-- Unit tests -->|
    |                         |                  |
  Real DB                  Fakes              Full mocks
  Real APIs              In-memory DB          Stubs
  Real FS                Test server           Spies
```

### Rules of Thumb

1. **Mock at the boundaries**: External services, I/O, network, file system, time
2. **Do not mock what you own** (when testing integration): If both the caller and callee are your code, test them together
3. **Do not mock what you do not own** (when unit testing): Instead, wrap third-party APIs in your own interface, then mock that
4. **One mock per test is ideal**: If you need more than 3 mocks, the unit under test may have too many dependencies
5. **Prefer fakes over mocks**: A fake (in-memory DB, test email service) catches more bugs than a mock that returns canned data
6. **Reset mocks between tests**: Use `jest.restoreAllMocks()` / `afterEach` cleanup to prevent mock leakage
7. **Verify interactions sparingly**: Assert on outputs, not on how many times something was called (except for side effects like sending emails)
