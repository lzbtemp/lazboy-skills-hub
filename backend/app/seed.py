"""Seed the database with initial categories and sample skills."""

from passlib.context import CryptContext
from slugify import slugify

from app.database import SessionLocal
from app.models import Category, Skill, Tag, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

CATEGORIES = [
    {"name": "Development", "icon": "code", "sort_order": 0},
    {"name": "DevOps", "icon": "server", "sort_order": 1},
    {"name": "Testing", "icon": "check-circle", "sort_order": 2},
    {"name": "Security", "icon": "shield", "sort_order": 3},
    {"name": "Data & Analytics", "icon": "database", "sort_order": 4},
    {"name": "AI / ML", "icon": "cpu", "sort_order": 5},
    {"name": "Frontend", "icon": "layout", "sort_order": 6},
    {"name": "Backend", "icon": "terminal", "sort_order": 7},
    {"name": "Infrastructure", "icon": "cloud", "sort_order": 8},
    {"name": "Documentation", "icon": "file-text", "sort_order": 9},
    {"name": "Design", "icon": "figma", "sort_order": 10},
    {"name": "Business", "icon": "briefcase", "sort_order": 11},
]

SAMPLE_SKILLS = [
    {
        "name": "Python Best Practices",
        "description": "Comprehensive guide for writing clean, maintainable Python code following PEP standards.",
        "content": """# Python Best Practices

## Overview
This skill provides guidelines for writing clean, maintainable Python code.

## Instructions
- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write docstrings for public functions
- Prefer composition over inheritance
- Use context managers for resource management

## Example
```python
def calculate_total(items: list[dict]) -> float:
    \"\"\"Calculate the total price of all items.\"\"\"
    return sum(item["price"] * item["quantity"] for item in items)
```
""",
        "category": "Development",
        "tags": ["python", "best-practices", "clean-code"],
    },
    {
        "name": "React Component Patterns",
        "description": "Modern React patterns including hooks, composition, and performance optimization.",
        "content": """# React Component Patterns

## Overview
Skill for building modern React components with hooks and composition patterns.

## Instructions
- Use functional components with hooks
- Implement custom hooks for shared logic
- Use React.memo for expensive components
- Prefer controlled components for forms
- Use error boundaries for fault tolerance

## Example
```tsx
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
```
""",
        "category": "Frontend",
        "tags": ["react", "typescript", "hooks"],
    },
    {
        "name": "Docker Deployment Guide",
        "description": "Best practices for containerizing applications with Docker and Docker Compose.",
        "content": """# Docker Deployment Guide

## Overview
Skill for containerizing and deploying applications using Docker.

## Instructions
- Use multi-stage builds to minimize image size
- Run as non-root user in production
- Use .dockerignore to exclude unnecessary files
- Pin base image versions
- Use health checks

## Example Dockerfile
```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
USER nobody
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```
""",
        "category": "DevOps",
        "tags": ["docker", "deployment", "containers"],
    },
    {
        "name": "API Security Checklist",
        "description": "Security checklist for REST APIs covering authentication, authorization, and OWASP Top 10.",
        "content": """# API Security Checklist

## Overview
Comprehensive security checklist for building secure REST APIs.

## Instructions
- Always validate and sanitize input
- Use HTTPS everywhere
- Implement rate limiting
- Use JWT with short expiration times
- Never expose stack traces in production
- Implement CORS properly
- Log security events

## Checklist
- [ ] Input validation on all endpoints
- [ ] Authentication required for protected routes
- [ ] Role-based authorization checks
- [ ] Rate limiting configured
- [ ] CORS whitelist configured
- [ ] SQL injection prevention
- [ ] XSS prevention headers set
""",
        "category": "Security",
        "tags": ["security", "api", "owasp"],
    },
    {
        "name": "Unit Testing Patterns",
        "description": "Patterns for writing effective unit tests with pytest including fixtures, mocking, and parameterization.",
        "content": """# Unit Testing Patterns

## Overview
Skill for writing clean, effective unit tests with pytest.

## Instructions
- Follow Arrange-Act-Assert pattern
- Use fixtures for test setup
- Mock external dependencies
- Use parameterize for data-driven tests
- Aim for high coverage on business logic

## Example
```python
import pytest

@pytest.fixture
def sample_user():
    return User(username="testuser", email="test@example.com")

@pytest.mark.parametrize("input,expected", [
    (0, "zero"),
    (1, "one"),
    (2, "other"),
])
def test_number_to_word(input, expected):
    assert number_to_word(input) == expected
```
""",
        "category": "Testing",
        "tags": ["testing", "pytest", "python"],
    },
]


def seed():
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Category).count() > 0:
            print("Database already seeded, skipping.")
            return

        # Seed categories
        categories = {}
        for cat_data in CATEGORIES:
            cat = Category(
                name=cat_data["name"],
                slug=slugify(cat_data["name"]),
                description=f"Skills related to {cat_data['name'].lower()}",
                icon=cat_data["icon"],
                sort_order=cat_data["sort_order"],
            )
            db.add(cat)
            db.flush()
            categories[cat_data["name"]] = cat

        # Seed a default admin user
        admin = User(
            username="admin",
            email="admin@lazboy.com",
            hashed_password=pwd_context.hash("admin123"),
            display_name="Admin User",
            role="admin",
        )
        db.add(admin)
        db.flush()

        # Seed tags and skills
        tag_cache: dict[str, Tag] = {}
        for skill_data in SAMPLE_SKILLS:
            tags = []
            for tag_name in skill_data["tags"]:
                if tag_name not in tag_cache:
                    tag = Tag(name=tag_name, slug=slugify(tag_name))
                    db.add(tag)
                    db.flush()
                    tag_cache[tag_name] = tag
                tags.append(tag_cache[tag_name])

            skill = Skill(
                name=skill_data["name"],
                slug=slugify(skill_data["name"]),
                description=skill_data["description"],
                content=skill_data["content"],
                category_id=categories[skill_data["category"]].id,
                author_id=admin.id,
                tags=tags,
            )
            db.add(skill)

        db.commit()
        print(f"Seeded {len(CATEGORIES)} categories, 1 admin user, {len(SAMPLE_SKILLS)} skills.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
