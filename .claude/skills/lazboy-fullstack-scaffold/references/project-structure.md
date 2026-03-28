# Full-Stack Project Structure Templates

## Overview

This reference provides production-ready directory layouts for common full-stack combinations. Each template includes conventions for shared types, API client generation, environment configuration, and monorepo tooling.

---

## 1. React + Express (Monorepo with Turborepo)

### Directory Layout

```
my-app/
├── apps/
│   ├── web/                          # React frontend (Vite)
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── ui/               # Generic UI components
│   │   │   │   └── features/         # Feature-specific components
│   │   │   ├── hooks/                # Custom React hooks
│   │   │   ├── pages/                # Route-level components
│   │   │   ├── services/             # API client functions
│   │   │   ├── stores/               # State management (Zustand/Redux)
│   │   │   ├── utils/                # Frontend utilities
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   ├── public/
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   │
│   └── api/                          # Express backend
│       ├── src/
│       │   ├── routes/               # Express route handlers
│       │   │   ├── auth.ts
│       │   │   ├── users.ts
│       │   │   └── index.ts
│       │   ├── middleware/            # Express middleware
│       │   │   ├── auth.ts
│       │   │   ├── error-handler.ts
│       │   │   ├── validation.ts
│       │   │   └── rate-limit.ts
│       │   ├── services/             # Business logic
│       │   ├── repositories/         # Data access layer
│       │   ├── config/               # App configuration
│       │   │   ├── database.ts
│       │   │   └── env.ts
│       │   ├── utils/
│       │   └── app.ts
│       ├── prisma/
│       │   ├── schema.prisma
│       │   └── migrations/
│       ├── tsconfig.json
│       └── package.json
│
├── packages/
│   ├── shared-types/                 # Shared TypeScript types
│   │   ├── src/
│   │   │   ├── api.ts                # Request/response types
│   │   │   ├── models.ts             # Domain model types
│   │   │   └── index.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   │
│   ├── ui/                           # Shared UI component library
│   │   ├── src/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   └── index.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   │
│   ├── eslint-config/                # Shared ESLint config
│   │   ├── base.js
│   │   ├── react.js
│   │   ├── node.js
│   │   └── package.json
│   │
│   └── tsconfig/                     # Shared TypeScript configs
│       ├── base.json
│       ├── react.json
│       ├── node.json
│       └── package.json
│
├── turbo.json                        # Turborepo configuration
├── package.json                      # Root workspace config
├── pnpm-workspace.yaml               # pnpm workspace definition
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

### Key Configuration Files

**turbo.json**
```json
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": [".env"],
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {
      "dependsOn": ["^build"]
    },
    "test": {
      "dependsOn": ["^build"]
    },
    "typecheck": {
      "dependsOn": ["^build"]
    }
  }
}
```

**pnpm-workspace.yaml**
```yaml
packages:
  - "apps/*"
  - "packages/*"
```

### Shared Types Pattern

```typescript
// packages/shared-types/src/api.ts
export interface ApiResponse<T> {
  data: T;
  meta?: {
    page: number;
    pageSize: number;
    total: number;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[]>;
}

// packages/shared-types/src/models.ts
export interface User {
  id: string;
  email: string;
  name: string;
  role: "admin" | "user";
  createdAt: string;
  updatedAt: string;
}

export interface CreateUserRequest {
  email: string;
  name: string;
  password: string;
}
```

---

## 2. Next.js Full-Stack

### Directory Layout

```
my-next-app/
├── src/
│   ├── app/                          # App Router
│   │   ├── (auth)/                   # Auth route group
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── register/
│   │   │       └── page.tsx
│   │   ├── (dashboard)/              # Dashboard route group
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── settings/
│   │   │       └── page.tsx
│   │   ├── api/                      # API routes
│   │   │   ├── auth/
│   │   │   │   └── [...nextauth]/
│   │   │   │       └── route.ts
│   │   │   ├── users/
│   │   │   │   ├── route.ts          # GET /api/users, POST /api/users
│   │   │   │   └── [id]/
│   │   │   │       └── route.ts      # GET/PUT/DELETE /api/users/:id
│   │   │   └── health/
│   │   │       └── route.ts
│   │   ├── layout.tsx                # Root layout
│   │   ├── page.tsx                  # Home page
│   │   ├── error.tsx                 # Error boundary
│   │   ├── loading.tsx               # Loading UI
│   │   ├── not-found.tsx
│   │   └── globals.css
│   │
│   ├── components/
│   │   ├── ui/                       # Reusable UI primitives
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── index.ts
│   │   ├── forms/                    # Form components
│   │   │   ├── login-form.tsx
│   │   │   └── user-form.tsx
│   │   └── layouts/                  # Layout components
│   │       ├── header.tsx
│   │       ├── sidebar.tsx
│   │       └── footer.tsx
│   │
│   ├── lib/                          # Core utilities and configuration
│   │   ├── db.ts                     # Database client (Prisma/Drizzle)
│   │   ├── auth.ts                   # Auth configuration
│   │   ├── api-client.ts             # Server-side API utilities
│   │   └── utils.ts                  # General helpers
│   │
│   ├── hooks/                        # Client-side React hooks
│   │   ├── use-auth.ts
│   │   └── use-debounce.ts
│   │
│   ├── services/                     # Business logic / server actions
│   │   ├── user-service.ts
│   │   └── auth-service.ts
│   │
│   ├── types/                        # TypeScript type definitions
│   │   ├── api.ts
│   │   ├── models.ts
│   │   └── next-auth.d.ts
│   │
│   └── middleware.ts                  # Next.js middleware (auth, etc.)
│
├── prisma/
│   ├── schema.prisma
│   ├── migrations/
│   └── seed.ts
│
├── public/
│   ├── favicon.ico
│   └── images/
│
├── tests/
│   ├── e2e/                          # Playwright end-to-end tests
│   │   └── auth.spec.ts
│   └── unit/                         # Vitest unit tests
│       └── services/
│           └── user-service.test.ts
│
├── next.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── tsconfig.json
├── package.json
├── docker-compose.yml
├── .env.example
├── .env.local                        # (gitignored)
└── .gitignore
```

### Server Actions Pattern (Next.js 14+)

```typescript
// src/services/user-service.ts
"use server";

import { db } from "@/lib/db";
import { revalidatePath } from "next/cache";
import { z } from "zod";

const CreateUserSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email(),
});

export async function createUser(formData: FormData) {
  const parsed = CreateUserSchema.safeParse({
    name: formData.get("name"),
    email: formData.get("email"),
  });

  if (!parsed.success) {
    return { error: parsed.error.flatten().fieldErrors };
  }

  const user = await db.user.create({
    data: parsed.data,
  });

  revalidatePath("/dashboard/users");
  return { data: user };
}
```

---

## 3. Python FastAPI + React

### Directory Layout

```
my-fullstack-app/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── users.py
│   │   │   │   │   └── health.py
│   │   │   │   ├── deps.py           # Dependency injection
│   │   │   │   └── router.py         # API router aggregation
│   │   │   └── __init__.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py             # Settings (pydantic-settings)
│   │   │   ├── security.py           # JWT, password hashing
│   │   │   └── exceptions.py         # Custom exception handlers
│   │   │
│   │   ├── db/
│   │   │   ├── base.py               # SQLAlchemy Base
│   │   │   ├── session.py            # Database session factory
│   │   │   └── migrations/           # Alembic migrations
│   │   │       ├── versions/
│   │   │       ├── env.py
│   │   │       └── alembic.ini
│   │   │
│   │   ├── models/                   # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── user.py
│   │   │   ├── auth.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── services/                 # Business logic
│   │   │   ├── user_service.py
│   │   │   └── auth_service.py
│   │   │
│   │   ├── repositories/            # Data access layer
│   │   │   └── user_repository.py
│   │   │
│   │   └── main.py                   # FastAPI application factory
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── api/
│   │   │   └── test_users.py
│   │   └── services/
│   │       └── test_user_service.py
│   │
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── alembic.ini
│
├── frontend/
│   ├── src/
│   │   ├── api/                      # Generated or hand-written API client
│   │   │   ├── client.ts             # Axios/fetch wrapper
│   │   │   ├── users.ts              # User API functions
│   │   │   └── types.ts              # API types (can be auto-generated)
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── stores/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── shared/
│   └── openapi.yaml                  # OpenAPI spec (source of truth)
│
├── scripts/
│   ├── generate-api-client.sh        # Generate TS client from OpenAPI
│   └── seed-db.py
│
├── docker-compose.yml
├── Makefile
├── .env.example
└── .gitignore
```

### API Client Generation

Generate a TypeScript client from the FastAPI OpenAPI spec:

```bash
# scripts/generate-api-client.sh
#!/usr/bin/env bash
set -euo pipefail

# Export OpenAPI schema from FastAPI
cd backend
python -c "
from app.main import app
import json
schema = app.openapi()
with open('../shared/openapi.yaml', 'w') as f:
    import yaml
    yaml.dump(schema, f, default_flow_style=False)
"

# Generate TypeScript client
cd ../frontend
npx openapi-typescript-codegen \
  --input ../shared/openapi.yaml \
  --output src/api/generated \
  --client axios
```

### Shared Schema Approach

```python
# backend/app/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

The Pydantic models produce a JSON Schema / OpenAPI spec that can be consumed by the TypeScript client generator, keeping frontend and backend types synchronized.

---

## 4. Spring Boot + React

### Directory Layout

```
my-spring-react-app/
├── backend/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/example/app/
│   │   │   │   ├── config/
│   │   │   │   │   ├── SecurityConfig.java
│   │   │   │   │   ├── CorsConfig.java
│   │   │   │   │   └── OpenApiConfig.java
│   │   │   │   │
│   │   │   │   ├── controller/
│   │   │   │   │   ├── AuthController.java
│   │   │   │   │   ├── UserController.java
│   │   │   │   │   └── HealthController.java
│   │   │   │   │
│   │   │   │   ├── service/
│   │   │   │   │   ├── UserService.java
│   │   │   │   │   └── AuthService.java
│   │   │   │   │
│   │   │   │   ├── repository/
│   │   │   │   │   └── UserRepository.java
│   │   │   │   │
│   │   │   │   ├── model/
│   │   │   │   │   ├── entity/
│   │   │   │   │   │   └── User.java
│   │   │   │   │   ├── dto/
│   │   │   │   │   │   ├── CreateUserRequest.java
│   │   │   │   │   │   ├── UserResponse.java
│   │   │   │   │   │   └── ApiError.java
│   │   │   │   │   └── mapper/
│   │   │   │   │       └── UserMapper.java
│   │   │   │   │
│   │   │   │   ├── exception/
│   │   │   │   │   ├── GlobalExceptionHandler.java
│   │   │   │   │   ├── ResourceNotFoundException.java
│   │   │   │   │   └── ValidationException.java
│   │   │   │   │
│   │   │   │   └── Application.java
│   │   │   │
│   │   │   └── resources/
│   │   │       ├── application.yml
│   │   │       ├── application-dev.yml
│   │   │       ├── application-prod.yml
│   │   │       └── db/migration/          # Flyway migrations
│   │   │           ├── V1__create_users.sql
│   │   │           └── V2__add_roles.sql
│   │   │
│   │   └── test/
│   │       └── java/com/example/app/
│   │           ├── controller/
│   │           │   └── UserControllerTest.java
│   │           ├── service/
│   │           │   └── UserServiceTest.java
│   │           └── repository/
│   │               └── UserRepositoryTest.java
│   │
│   ├── build.gradle.kts               # or pom.xml
│   ├── Dockerfile
│   └── settings.gradle.kts
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── generated/             # Auto-generated from OpenAPI
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── docker-compose.yml
├── Makefile
├── .env.example
└── .gitignore
```

### Spring Boot OpenAPI Integration

```java
// config/OpenApiConfig.java
@Configuration
public class OpenApiConfig {
    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
            .info(new Info()
                .title("My App API")
                .version("1.0.0")
                .description("API documentation"));
    }
}
```

Generate the TypeScript client using the `/v3/api-docs` endpoint:

```bash
npx openapi-typescript-codegen \
  --input http://localhost:8080/v3/api-docs \
  --output frontend/src/api/generated \
  --client axios
```

---

## 5. Environment Configuration

### Multi-Environment Strategy

```
.env.example          # Template with all variables (committed)
.env                  # Local development overrides (gitignored)
.env.test             # Test environment variables
.env.staging          # Staging variables (in CI/CD secrets)
.env.production       # Production variables (in CI/CD secrets)
```

### Environment Variable Naming Convention

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp_dev
DB_USER=myapp
DB_PASSWORD=localdev

# Auth
AUTH_JWT_SECRET=local-dev-secret-change-in-prod
AUTH_JWT_EXPIRY=3600

# External services
REDIS_URL=redis://localhost:6379
S3_BUCKET=myapp-uploads-dev

# Feature flags
FEATURE_NEW_DASHBOARD=true

# App
APP_PORT=3000
APP_LOG_LEVEL=debug
```

---

## 6. Monorepo Tooling Comparison

### Turborepo vs Nx

| Feature | Turborepo | Nx |
|---|---|---|
| Setup complexity | Low | Medium |
| Build caching | Remote + local | Remote + local |
| Task orchestration | Pipeline-based | Graph-based |
| Code generation | None built-in | Extensive generators |
| Language support | JavaScript/TypeScript | Multi-language |
| Plugin ecosystem | Minimal | Extensive |
| Best for | JS/TS monorepos | Large multi-language repos |

### Turborepo Setup

```bash
# Initialize
npx create-turbo@latest

# Run tasks across all packages
turbo run build
turbo run test --filter=./apps/web
turbo run dev --filter=./apps/api

# Add a new package
mkdir packages/new-lib && cd packages/new-lib
npm init -y
```

### Nx Setup

```bash
# Initialize
npx create-nx-workspace@latest my-app --preset=ts

# Generate an application
nx generate @nx/react:app web
nx generate @nx/express:app api

# Run tasks
nx run-many --target=build
nx affected --target=test
nx graph  # Visualize dependencies
```

---

## 7. Docker Compose for Development

### Full-Stack Docker Compose

```yaml
# docker-compose.yml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
    environment:
      - VITE_API_URL=http://localhost:8080
    depends_on:
      - api

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8080:8080"
    volumes:
      - ./backend/src:/app/src
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=myapp
      - DB_USER=myapp
      - DB_PASSWORD=localdev
      - REDIS_URL=redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: myapp
      POSTGRES_PASSWORD: localdev
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myapp"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

---

## 8. CI Workflow Integration

### GitHub Actions for Monorepo

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      frontend: ${{ steps.filter.outputs.frontend }}
      backend: ${{ steps.filter.outputs.backend }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            frontend:
              - 'frontend/**'
              - 'packages/shared-types/**'
            backend:
              - 'backend/**'
              - 'packages/shared-types/**'

  frontend:
    needs: changes
    if: needs.changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm turbo run lint typecheck test build --filter=./apps/web...

  backend:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Add backend-specific CI steps here
```
