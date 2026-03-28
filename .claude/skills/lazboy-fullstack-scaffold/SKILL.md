---
name: lazboy-fullstack-scaffold
description: "Scaffold full-stack La-Z-Boy applications with React frontend and FastAPI backend. Includes project structure, environment setup, development workflow, deployment configuration, and integration patterns. Use when starting a new project or microservice."
version: "1.0.0"
category: Full Stack
tags: [fullstack, react, fastapi, scaffold]
---

# La-Z-Boy Full Stack Scaffold Skill

Scaffold production-ready full-stack applications following La-Z-Boy engineering standards.

**Reference files — load when needed:**
- `references/project-structure.md` — standard project layout
- `references/environment-setup.md` — environment variables and config

**Scripts — run when needed:**
- `scripts/scaffold_project.py` — generate a new project from template
- `scripts/setup_dev.sh` — configure local development environment

---

## 1. Project Structure

```
project-name/
├── frontend/
│   ├── src/
│   │   ├── api/           # API client and types
│   │   ├── components/    # Reusable UI components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── pages/         # Route-level components
│   │   ├── types/         # TypeScript types
│   │   └── utils/         # Helper functions
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── backend/
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── core/          # Config, security, deps
│   ├── alembic/           # Database migrations
│   ├── tests/
│   └── pyproject.toml
├── docker-compose.yml
├── Makefile
└── README.md
```

## 2. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite | Fast builds, type safety |
| Styling | Tailwind CSS | Utility-first, brand tokens |
| State | TanStack Query + Zustand | Server/client state separation |
| Backend | FastAPI + Python 3.11+ | Async, auto-docs, type hints |
| Database | PostgreSQL + SQLAlchemy | Reliable, async support |
| Cache | Redis | Session, rate limiting |
| Auth | Azure AD + JWT | SSO integration |

## 3. Environment Configuration

```env
# .env.example
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_CLIENT_ID=your-client-id
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

## 4. Development Workflow

```bash
# Start everything
make dev

# Frontend only
cd frontend && npm run dev

# Backend only
cd backend && uvicorn app.main:app --reload

# Run all tests
make test

# Database migration
cd backend && alembic revision --autogenerate -m "description"
cd backend && alembic upgrade head
```

## 5. Makefile Template

```makefile
.PHONY: dev test lint build deploy

dev:
	docker-compose up -d db redis
	cd backend && uvicorn app.main:app --reload &
	cd frontend && npm run dev

test:
	cd backend && pytest -v
	cd frontend && npm test

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

build:
	cd frontend && npm run build
	docker build -t project-name .
```

## 6. API Integration Pattern

```typescript
// frontend/src/api/client.ts
const api = {
  async get<T>(path: string): Promise<T> {
    const res = await fetch(`/api/v1${path}`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    if (!res.ok) throw new ApiError(res);
    return res.json();
  }
};
```
