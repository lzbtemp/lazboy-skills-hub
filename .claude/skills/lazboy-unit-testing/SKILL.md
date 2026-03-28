---
name: lazboy-unit-testing
description: "Write effective unit tests for La-Z-Boy applications. Covers Jest/Vitest for frontend, pytest for backend, mocking strategies, test structure, and coverage requirements. Use when writing unit tests or improving test quality."
version: "1.0.0"
category: QA/Testing
tags: [testing, qa, jest, pytest, unit-tests]
---

# La-Z-Boy Unit Testing Skill

Standards for writing effective unit tests across La-Z-Boy applications.

**Reference files — load when needed:**
- `references/testing-patterns.md` — approved unit test patterns
- `references/mocking-guide.md` — when and how to mock dependencies

**Scripts — run when needed:**
- `scripts/generate_tests.py` — auto-generate test stubs from source files
- `scripts/coverage_report.py` — generate detailed coverage report

---

## 1. Test Structure (AAA Pattern)

```typescript
describe('SkillService', () => {
  it('should return skills filtered by category', () => {
    // Arrange
    const skills = [
      { name: 'react-component', category: 'Frontend' },
      { name: 'api-gateway', category: 'Backend' },
    ];

    // Act
    const result = filterByCategory(skills, 'Frontend');

    // Assert
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('react-component');
  });
});
```

## 2. Frontend Testing (Vitest + React Testing Library)

### Component Test
```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SkillCard from './SkillCard';

describe('SkillCard', () => {
  const mockSkill = {
    name: 'lazboy-brand',
    description: 'Brand standards skill',
    category: { name: 'Designer' },
    tags: [{ id: 1, name: 'design', slug: 'design' }],
  };

  it('renders skill name and description', () => {
    render(<SkillCard skill={mockSkill} />);
    expect(screen.getByText('lazboy-brand')).toBeInTheDocument();
    expect(screen.getByText(/Brand standards/)).toBeInTheDocument();
  });

  it('navigates to skill detail on click', () => {
    render(<SkillCard skill={mockSkill} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/skills/lazboy-brand');
  });
});
```

### Hook Test
```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useSkills } from './useSkills';

describe('useSkills', () => {
  it('returns paginated skills', async () => {
    const { result } = renderHook(() => useSkills({ page: 1 }));
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data.total).toBeGreaterThan(0);
  });
});
```

## 3. Backend Testing (pytest)

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

class TestSkillsAPI:
    async def test_list_skills(self, client):
        response = await client.get("/api/v1/skills")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_create_skill_validation(self, client):
        response = await client.post("/api/v1/skills", json={})
        assert response.status_code == 422

    async def test_get_skill_not_found(self, client):
        response = await client.get("/api/v1/skills/99999")
        assert response.status_code == 404
```

## 4. Mocking Rules

### When to Mock
- External APIs and services
- Database calls in unit tests
- Time-dependent functions
- File system operations

### When NOT to Mock
- Pure functions and utilities
- Data transformations
- Simple class methods
- The thing you're testing

## 5. Coverage Requirements

| Code Type | Minimum Coverage |
|---|---|
| Business logic | 90% |
| API endpoints | 85% |
| UI components | 80% |
| Utility functions | 95% |
| Configuration | Not required |

## 6. Test Naming Convention

```
it('should [expected behavior] when [condition]')
```

Examples:
- `it('should return empty array when no skills match category')`
- `it('should throw error when database connection fails')`
- `it('should display loading spinner when data is fetching')`
