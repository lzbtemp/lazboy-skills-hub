---
name: lazboy-api-gateway
description: "Build and maintain RESTful APIs following La-Z-Boy backend standards. Covers FastAPI/Express patterns, authentication, rate limiting, error handling, OpenAPI documentation, and database integration. Use when creating any backend service or API endpoint."
version: "1.0.0"
category: Backend
tags: [backend, api, fastapi, rest]
---

# La-Z-Boy API Gateway Skill

Standards for building production-ready APIs at La-Z-Boy.

**Reference files — load when needed:**
- `references/api-patterns.md` — approved API design patterns
- `references/error-codes.md` — standardized error response codes

**Scripts — run when needed:**
- `scripts/generate_endpoint.py` — scaffold a new API endpoint with tests
- `scripts/validate_openapi.py` — validate OpenAPI spec against standards

---

## 1. API Design Standards

### URL Structure
```
/api/v1/{resource}          # Collection
/api/v1/{resource}/{id}     # Single resource
/api/v1/{resource}/{id}/{sub-resource}  # Nested resource
```

### HTTP Methods
| Method | Purpose | Response Code |
|---|---|---|
| GET | Read | 200 |
| POST | Create | 201 |
| PUT | Full update | 200 |
| PATCH | Partial update | 200 |
| DELETE | Remove | 204 |

### Naming Conventions
- Use kebab-case for URLs: `/api/v1/product-categories`
- Use snake_case for JSON fields: `{ "product_name": "..." }`
- Plural nouns for collections: `/skills` not `/skill`

## 2. FastAPI Endpoint Template

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    category: str

class SkillResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

@router.post("/", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: SkillCreate,
    db: AsyncSession = Depends(get_db),
):
    skill = Skill(**payload.model_dump())
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill
```

## 3. Error Handling

All errors must return consistent JSON:

```json
{
  "error": {
    "code": "SKILL_NOT_FOUND",
    "message": "Skill with id 42 was not found",
    "status": 404
  }
}
```

## 4. Authentication

- Internal APIs: JWT tokens via Azure AD
- Service-to-service: API keys in `X-API-Key` header
- Never expose secrets in URLs or logs

## 5. Rate Limiting

- Public endpoints: 100 requests/minute
- Authenticated endpoints: 1000 requests/minute
- Return `429 Too Many Requests` with `Retry-After` header

## 6. Database Integration

- Use async SQLAlchemy with PostgreSQL
- Always use parameterized queries (never string interpolation)
- Add indexes for frequently queried columns
- Use Alembic for migrations
