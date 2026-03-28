#!/usr/bin/env python3
"""Scaffold a full-stack project skeleton.

Usage:
    python scaffold_project.py --name my-app --frontend react --backend express
    python scaffold_project.py --name my-app --frontend next --backend fastapi
    python scaffold_project.py --name my-app --frontend react --backend spring --output-dir ./projects

Generates:
    - Directory structure for the chosen stack
    - package.json / pyproject.toml / build.gradle.kts
    - Docker Compose with PostgreSQL and Redis
    - .gitignore, .editorconfig, .env.example
    - CI workflow (GitHub Actions)
    - README with setup instructions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent

FRONTEND_CHOICES = ("react", "next")
BACKEND_CHOICES = ("express", "fastapi", "spring")

# ---------------------------------------------------------------------------
# Frontend templates
# ---------------------------------------------------------------------------


def _react_files(name: str) -> dict[str, str]:
    """Generate files for a Vite + React + TypeScript frontend."""
    return {
        "frontend/package.json": dedent(f"""\
            {{
              "name": "{name}-frontend",
              "private": true,
              "version": "0.1.0",
              "type": "module",
              "scripts": {{
                "dev": "vite",
                "build": "tsc -b && vite build",
                "preview": "vite preview",
                "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
                "typecheck": "tsc --noEmit"
              }},
              "dependencies": {{
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
                "react-router-dom": "^6.26.0",
                "@tanstack/react-query": "^5.51.0",
                "axios": "^1.7.0",
                "clsx": "^2.1.1"
              }},
              "devDependencies": {{
                "@types/react": "^18.3.3",
                "@types/react-dom": "^18.3.0",
                "@vitejs/plugin-react": "^4.3.1",
                "eslint": "^9.8.0",
                "typescript": "^5.5.4",
                "vite": "^5.4.0",
                "@eslint/js": "^9.8.0",
                "prettier": "^3.3.3"
              }}
            }}
        """),
        "frontend/tsconfig.json": dedent("""\
            {
              "compilerOptions": {
                "target": "ES2020",
                "useDefineForClassFields": true,
                "lib": ["ES2020", "DOM", "DOM.Iterable"],
                "module": "ESNext",
                "skipLibCheck": true,
                "moduleResolution": "bundler",
                "allowImportingTsExtensions": true,
                "isolatedModules": true,
                "moduleDetection": "force",
                "noEmit": true,
                "jsx": "react-jsx",
                "strict": true,
                "noUnusedLocals": true,
                "noUnusedParameters": true,
                "noFallthroughCasesInSwitch": true,
                "baseUrl": ".",
                "paths": {
                  "@/*": ["src/*"]
                }
              },
              "include": ["src"]
            }
        """),
        "frontend/vite.config.ts": dedent("""\
            import { defineConfig } from "vite";
            import react from "@vitejs/plugin-react";
            import path from "path";

            export default defineConfig({
              plugins: [react()],
              resolve: {
                alias: {
                  "@": path.resolve(__dirname, "./src"),
                },
              },
              server: {
                port: 3000,
                proxy: {
                  "/api": {
                    target: "http://localhost:8080",
                    changeOrigin: true,
                  },
                },
              },
            });
        """),
        "frontend/index.html": dedent(f"""\
            <!doctype html>
            <html lang="en">
              <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>{name}</title>
              </head>
              <body>
                <div id="root"></div>
                <script type="module" src="/src/main.tsx"></script>
              </body>
            </html>
        """),
        "frontend/src/main.tsx": dedent("""\
            import React from "react";
            import ReactDOM from "react-dom/client";
            import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
            import App from "./App";

            const queryClient = new QueryClient({
              defaultOptions: {
                queries: {
                  staleTime: 5 * 60 * 1000,
                  retry: 1,
                },
              },
            });

            ReactDOM.createRoot(document.getElementById("root")!).render(
              <React.StrictMode>
                <QueryClientProvider client={queryClient}>
                  <App />
                </QueryClientProvider>
              </React.StrictMode>,
            );
        """),
        "frontend/src/App.tsx": dedent("""\
            import { BrowserRouter, Routes, Route } from "react-router-dom";

            function HomePage() {
              return (
                <div>
                  <h1>Welcome</h1>
                  <p>Your full-stack app is running.</p>
                </div>
              );
            }

            export default function App() {
              return (
                <BrowserRouter>
                  <Routes>
                    <Route path="/" element={<HomePage />} />
                  </Routes>
                </BrowserRouter>
              );
            }
        """),
        "frontend/src/api/client.ts": dedent("""\
            import axios from "axios";

            const apiClient = axios.create({
              baseURL: import.meta.env.VITE_API_URL || "/api",
              timeout: 10_000,
              headers: {
                "Content-Type": "application/json",
              },
            });

            apiClient.interceptors.response.use(
              (response) => response,
              (error) => {
                if (error.response?.status === 401) {
                  window.location.href = "/login";
                }
                return Promise.reject(error);
              },
            );

            export default apiClient;
        """),
    }


def _next_files(name: str) -> dict[str, str]:
    """Generate files for a Next.js full-stack frontend."""
    return {
        "frontend/package.json": dedent(f"""\
            {{
              "name": "{name}-frontend",
              "private": true,
              "version": "0.1.0",
              "scripts": {{
                "dev": "next dev --port 3000",
                "build": "next build",
                "start": "next start",
                "lint": "next lint",
                "typecheck": "tsc --noEmit"
              }},
              "dependencies": {{
                "next": "^14.2.0",
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
                "@tanstack/react-query": "^5.51.0",
                "clsx": "^2.1.1",
                "zod": "^3.23.0"
              }},
              "devDependencies": {{
                "@types/react": "^18.3.3",
                "@types/react-dom": "^18.3.0",
                "typescript": "^5.5.4",
                "eslint": "^9.8.0",
                "eslint-config-next": "^14.2.0",
                "prettier": "^3.3.3"
              }}
            }}
        """),
        "frontend/tsconfig.json": dedent("""\
            {
              "compilerOptions": {
                "target": "ES2017",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": true,
                "skipLibCheck": true,
                "strict": true,
                "noEmit": true,
                "esModuleInterop": true,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": true,
                "isolatedModules": true,
                "jsx": "preserve",
                "incremental": true,
                "plugins": [{ "name": "next" }],
                "paths": {
                  "@/*": ["./src/*"]
                }
              },
              "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
              "exclude": ["node_modules"]
            }
        """),
        "frontend/next.config.ts": dedent("""\
            import type { NextConfig } from "next";

            const nextConfig: NextConfig = {
              reactStrictMode: true,
              async rewrites() {
                return [
                  {
                    source: "/api/:path*",
                    destination: "http://localhost:8080/api/:path*",
                  },
                ];
              },
            };

            export default nextConfig;
        """),
        "frontend/src/app/layout.tsx": dedent(f"""\
            import type {{ Metadata }} from "next";

            export const metadata: Metadata = {{
              title: "{name}",
              description: "Full-stack application",
            }};

            export default function RootLayout({{
              children,
            }}: {{
              children: React.ReactNode;
            }}) {{
              return (
                <html lang="en">
                  <body>{{children}}</body>
                </html>
              );
            }}
        """),
        "frontend/src/app/page.tsx": dedent("""\
            export default function Home() {
              return (
                <main>
                  <h1>Welcome</h1>
                  <p>Your full-stack app is running.</p>
                </main>
              );
            }
        """),
    }


# ---------------------------------------------------------------------------
# Backend templates
# ---------------------------------------------------------------------------


def _express_files(name: str) -> dict[str, str]:
    """Generate files for an Express + TypeScript backend."""
    return {
        "backend/package.json": dedent(f"""\
            {{
              "name": "{name}-backend",
              "private": true,
              "version": "0.1.0",
              "type": "module",
              "scripts": {{
                "dev": "tsx watch src/app.ts",
                "build": "tsc",
                "start": "node dist/app.js",
                "lint": "eslint src/ --ext .ts",
                "typecheck": "tsc --noEmit",
                "test": "vitest run",
                "test:watch": "vitest",
                "db:migrate": "prisma migrate dev",
                "db:seed": "tsx prisma/seed.ts",
                "db:studio": "prisma studio"
              }},
              "dependencies": {{
                "express": "^4.19.0",
                "cors": "^2.8.5",
                "helmet": "^7.1.0",
                "compression": "^1.7.4",
                "morgan": "^1.10.0",
                "zod": "^3.23.0",
                "@prisma/client": "^5.18.0",
                "dotenv": "^16.4.0",
                "jsonwebtoken": "^9.0.2",
                "bcryptjs": "^2.4.3"
              }},
              "devDependencies": {{
                "@types/express": "^4.17.21",
                "@types/cors": "^2.8.17",
                "@types/compression": "^1.7.5",
                "@types/morgan": "^1.9.9",
                "@types/jsonwebtoken": "^9.0.6",
                "@types/bcryptjs": "^2.4.6",
                "typescript": "^5.5.4",
                "tsx": "^4.16.0",
                "prisma": "^5.18.0",
                "vitest": "^2.0.0",
                "supertest": "^7.0.0",
                "@types/supertest": "^6.0.2"
              }}
            }}
        """),
        "backend/tsconfig.json": dedent("""\
            {
              "compilerOptions": {
                "target": "ES2022",
                "module": "ESNext",
                "moduleResolution": "bundler",
                "outDir": "dist",
                "rootDir": "src",
                "strict": true,
                "esModuleInterop": true,
                "skipLibCheck": true,
                "forceConsistentCasingInFileNames": true,
                "resolveJsonModule": true,
                "declaration": true,
                "declarationMap": true,
                "sourceMap": true
              },
              "include": ["src"],
              "exclude": ["node_modules", "dist"]
            }
        """),
        "backend/src/app.ts": dedent(f"""\
            import express from "express";
            import cors from "cors";
            import helmet from "helmet";
            import compression from "compression";
            import morgan from "morgan";
            import {{ config }} from "./config/env.js";
            import {{ errorHandler }} from "./middleware/error-handler.js";
            import {{ healthRouter }} from "./routes/health.js";
            import {{ usersRouter }} from "./routes/users.js";

            const app = express();

            // Middleware
            app.use(helmet());
            app.use(cors({{ origin: config.CORS_ORIGIN }}));
            app.use(compression());
            app.use(express.json({{ limit: "10mb" }}));
            app.use(morgan(config.NODE_ENV === "production" ? "combined" : "dev"));

            // Routes
            app.use("/api/health", healthRouter);
            app.use("/api/users", usersRouter);

            // Error handling
            app.use(errorHandler);

            // Start server
            const port = config.PORT;
            app.listen(port, () => {{
              console.log(`Server running on port ${{port}} [${{config.NODE_ENV}}]`);
            }});

            export default app;
        """),
        "backend/src/config/env.ts": dedent("""\
            import { z } from "zod";
            import "dotenv/config";

            const envSchema = z.object({
              NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
              PORT: z.coerce.number().default(8080),
              DATABASE_URL: z.string().url(),
              JWT_SECRET: z.string().min(32),
              CORS_ORIGIN: z.string().default("http://localhost:3000"),
            });

            export const config = envSchema.parse(process.env);
            export type Config = z.infer<typeof envSchema>;
        """),
        "backend/src/middleware/error-handler.ts": dedent("""\
            import type { Request, Response, NextFunction } from "express";
            import { ZodError } from "zod";

            export class AppError extends Error {
              constructor(
                public statusCode: number,
                message: string,
                public code?: string,
              ) {
                super(message);
                this.name = "AppError";
              }
            }

            export function errorHandler(
              err: Error,
              _req: Request,
              res: Response,
              _next: NextFunction,
            ) {
              if (err instanceof AppError) {
                return res.status(err.statusCode).json({
                  error: { code: err.code || "APP_ERROR", message: err.message },
                });
              }

              if (err instanceof ZodError) {
                return res.status(400).json({
                  error: {
                    code: "VALIDATION_ERROR",
                    message: "Invalid request data",
                    details: err.flatten().fieldErrors,
                  },
                });
              }

              console.error("Unhandled error:", err);
              return res.status(500).json({
                error: { code: "INTERNAL_ERROR", message: "Internal server error" },
              });
            }
        """),
        "backend/src/routes/health.ts": dedent("""\
            import { Router } from "express";

            export const healthRouter = Router();

            healthRouter.get("/", (_req, res) => {
              res.json({ status: "ok", timestamp: new Date().toISOString() });
            });
        """),
        "backend/src/routes/users.ts": dedent("""\
            import { Router } from "express";
            import { z } from "zod";

            export const usersRouter = Router();

            const CreateUserSchema = z.object({
              email: z.string().email(),
              name: z.string().min(1).max(100),
            });

            usersRouter.get("/", async (_req, res, next) => {
              try {
                // TODO: Implement with Prisma
                res.json({ data: [], meta: { total: 0 } });
              } catch (err) {
                next(err);
              }
            });

            usersRouter.post("/", async (req, res, next) => {
              try {
                const body = CreateUserSchema.parse(req.body);
                // TODO: Implement with Prisma
                res.status(201).json({ data: { ...body, id: "generated" } });
              } catch (err) {
                next(err);
              }
            });
        """),
        "backend/prisma/schema.prisma": dedent("""\
            generator client {
              provider = "prisma-client-js"
            }

            datasource db {
              provider = "postgresql"
              url      = env("DATABASE_URL")
            }

            model User {
              id        String   @id @default(cuid())
              email     String   @unique
              name      String
              role      String   @default("user")
              createdAt DateTime @default(now()) @map("created_at")
              updatedAt DateTime @updatedAt @map("updated_at")

              @@map("users")
            }
        """),
    }


def _fastapi_files(name: str) -> dict[str, str]:
    """Generate files for a FastAPI backend."""
    return {
        "backend/pyproject.toml": dedent(f"""\
            [build-system]
            requires = ["setuptools>=68.0"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "{name}-backend"
            version = "0.1.0"
            requires-python = ">=3.11"
            dependencies = [
                "fastapi>=0.112.0",
                "uvicorn[standard]>=0.30.0",
                "pydantic>=2.8.0",
                "pydantic-settings>=2.4.0",
                "sqlalchemy>=2.0.31",
                "alembic>=1.13.0",
                "psycopg2-binary>=2.9.9",
                "python-jose[cryptography]>=3.3.0",
                "passlib[bcrypt]>=1.7.4",
                "httpx>=0.27.0",
            ]

            [project.optional-dependencies]
            dev = [
                "pytest>=8.3.0",
                "pytest-asyncio>=0.23.0",
                "httpx>=0.27.0",
                "ruff>=0.5.0",
                "mypy>=1.11.0",
            ]

            [tool.pytest.ini_options]
            testpaths = ["tests"]
            asyncio_mode = "auto"

            [tool.ruff]
            line-length = 100
            target-version = "py311"

            [tool.ruff.lint]
            select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "ASYNC"]

            [tool.mypy]
            python_version = "3.11"
            strict = true
        """),
        "backend/app/__init__.py": "",
        "backend/app/main.py": dedent(f"""\
            \"\"\"FastAPI application factory for {name}.\"\"\"

            from contextlib import asynccontextmanager

            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware

            from app.api.v1.router import api_router
            from app.core.config import get_settings


            @asynccontextmanager
            async def lifespan(app: FastAPI):
                # Startup logic
                yield
                # Shutdown logic


            def create_app() -> FastAPI:
                settings = get_settings()
                app = FastAPI(
                    title="{name} API",
                    version="0.1.0",
                    lifespan=lifespan,
                )
                app.add_middleware(
                    CORSMiddleware,
                    allow_origins=[settings.CORS_ORIGIN],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
                app.include_router(api_router, prefix="/api/v1")
                return app


            app = create_app()
        """),
        "backend/app/core/__init__.py": "",
        "backend/app/core/config.py": dedent("""\
            from functools import lru_cache

            from pydantic_settings import BaseSettings


            class Settings(BaseSettings):
                APP_ENV: str = "development"
                DATABASE_URL: str = "postgresql://myapp:localdev@localhost:5432/myapp_dev"
                JWT_SECRET: str = "change-me-in-production-use-a-long-random-string"
                JWT_ALGORITHM: str = "HS256"
                JWT_EXPIRY_MINUTES: int = 60
                CORS_ORIGIN: str = "http://localhost:3000"

                model_config = {"env_file": ".env"}


            @lru_cache
            def get_settings() -> Settings:
                return Settings()
        """),
        "backend/app/api/__init__.py": "",
        "backend/app/api/v1/__init__.py": "",
        "backend/app/api/v1/router.py": dedent("""\
            from fastapi import APIRouter

            from app.api.v1.endpoints import health, users

            api_router = APIRouter()
            api_router.include_router(health.router, prefix="/health", tags=["health"])
            api_router.include_router(users.router, prefix="/users", tags=["users"])
        """),
        "backend/app/api/v1/endpoints/__init__.py": "",
        "backend/app/api/v1/endpoints/health.py": dedent("""\
            from datetime import datetime, timezone

            from fastapi import APIRouter

            router = APIRouter()


            @router.get("/")
            def health_check():
                return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
        """),
        "backend/app/api/v1/endpoints/users.py": dedent("""\
            from fastapi import APIRouter, HTTPException
            from pydantic import BaseModel, EmailStr

            router = APIRouter()


            class CreateUserRequest(BaseModel):
                email: EmailStr
                name: str


            class UserResponse(BaseModel):
                id: str
                email: str
                name: str
                role: str


            @router.get("/")
            def list_users():
                # TODO: Implement with SQLAlchemy
                return {"data": [], "meta": {"total": 0}}


            @router.post("/", status_code=201)
            def create_user(body: CreateUserRequest):
                # TODO: Implement with SQLAlchemy
                return UserResponse(id="generated", email=body.email, name=body.name, role="user")
        """),
        "backend/app/models/__init__.py": "",
        "backend/app/schemas/__init__.py": "",
        "backend/app/services/__init__.py": "",
        "backend/tests/__init__.py": "",
        "backend/tests/conftest.py": dedent("""\
            import pytest
            from fastapi.testclient import TestClient

            from app.main import app


            @pytest.fixture
            def client():
                return TestClient(app)
        """),
        "backend/tests/test_health.py": dedent("""\
            def test_health_check(client):
                response = client.get("/api/v1/health/")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
        """),
        "backend/Dockerfile": dedent("""\
            FROM python:3.12-slim

            WORKDIR /app

            RUN apt-get update && apt-get install -y --no-install-recommends \\
                build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

            COPY pyproject.toml .
            RUN pip install --no-cache-dir -e .

            COPY . .

            RUN useradd --create-home appuser
            USER appuser

            EXPOSE 8080
            CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
        """),
    }


def _spring_files(name: str) -> dict[str, str]:
    """Generate files for a Spring Boot backend."""
    pkg = name.replace("-", "").replace("_", "")
    return {
        "backend/build.gradle.kts": dedent(f"""\
            plugins {{
                java
                id("org.springframework.boot") version "3.3.2"
                id("io.spring.dependency-management") version "1.1.6"
            }}

            group = "com.example"
            version = "0.1.0"

            java {{
                toolchain {{
                    languageVersion.set(JavaLanguageVersion.of(21))
                }}
            }}

            repositories {{
                mavenCentral()
            }}

            dependencies {{
                implementation("org.springframework.boot:spring-boot-starter-web")
                implementation("org.springframework.boot:spring-boot-starter-data-jpa")
                implementation("org.springframework.boot:spring-boot-starter-validation")
                implementation("org.springframework.boot:spring-boot-starter-security")
                implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.6.0")
                runtimeOnly("org.postgresql:postgresql")
                runtimeOnly("org.flywaydb:flyway-core")
                runtimeOnly("org.flywaydb:flyway-database-postgresql")

                testImplementation("org.springframework.boot:spring-boot-starter-test")
                testImplementation("org.springframework.security:spring-security-test")
            }}

            tasks.withType<Test> {{
                useJUnitPlatform()
            }}
        """),
        "backend/settings.gradle.kts": dedent(f"""\
            rootProject.name = "{name}-backend"
        """),
        f"backend/src/main/java/com/example/{pkg}/Application.java": dedent(f"""\
            package com.example.{pkg};

            import org.springframework.boot.SpringApplication;
            import org.springframework.boot.autoconfigure.SpringBootApplication;

            @SpringBootApplication
            public class Application {{
                public static void main(String[] args) {{
                    SpringApplication.run(Application.class, args);
                }}
            }}
        """),
        f"backend/src/main/java/com/example/{pkg}/controller/HealthController.java": dedent(f"""\
            package com.example.{pkg}.controller;

            import org.springframework.web.bind.annotation.GetMapping;
            import org.springframework.web.bind.annotation.RequestMapping;
            import org.springframework.web.bind.annotation.RestController;

            import java.time.Instant;
            import java.util.Map;

            @RestController
            @RequestMapping("/api/health")
            public class HealthController {{

                @GetMapping
                public Map<String, String> health() {{
                    return Map.of(
                        "status", "ok",
                        "timestamp", Instant.now().toString()
                    );
                }}
            }}
        """),
        f"backend/src/main/java/com/example/{pkg}/controller/UserController.java": dedent(f"""\
            package com.example.{pkg}.controller;

            import org.springframework.http.HttpStatus;
            import org.springframework.web.bind.annotation.*;

            import java.util.List;
            import java.util.Map;

            @RestController
            @RequestMapping("/api/users")
            public class UserController {{

                @GetMapping
                public Map<String, Object> listUsers() {{
                    return Map.of("data", List.of(), "meta", Map.of("total", 0));
                }}

                @PostMapping
                @ResponseStatus(HttpStatus.CREATED)
                public Map<String, String> createUser(@RequestBody Map<String, String> body) {{
                    // TODO: Implement with JPA repository
                    return Map.of(
                        "id", "generated",
                        "email", body.getOrDefault("email", ""),
                        "name", body.getOrDefault("name", ""),
                        "role", "user"
                    );
                }}
            }}
        """),
        "backend/src/main/resources/application.yml": dedent("""\
            server:
              port: 8080

            spring:
              datasource:
                url: ${DATABASE_URL:jdbc:postgresql://localhost:5432/myapp_dev}
                username: ${DB_USER:myapp}
                password: ${DB_PASSWORD:localdev}
              jpa:
                hibernate:
                  ddl-auto: validate
                open-in-view: false
              flyway:
                enabled: true

            springdoc:
              api-docs:
                path: /v3/api-docs
              swagger-ui:
                path: /swagger-ui.html
        """),
        "backend/src/main/resources/db/migration/V1__create_users.sql": dedent("""\
            CREATE TABLE users (
                id         VARCHAR(36)  PRIMARY KEY DEFAULT gen_random_uuid()::text,
                email      VARCHAR(255) NOT NULL UNIQUE,
                name       VARCHAR(100) NOT NULL,
                role       VARCHAR(20)  NOT NULL DEFAULT 'user',
                created_at TIMESTAMP    NOT NULL DEFAULT now(),
                updated_at TIMESTAMP    NOT NULL DEFAULT now()
            );
        """),
        "backend/Dockerfile": dedent("""\
            FROM eclipse-temurin:21-jdk-alpine AS build
            WORKDIR /app
            COPY . .
            RUN ./gradlew bootJar --no-daemon

            FROM eclipse-temurin:21-jre-alpine
            WORKDIR /app
            COPY --from=build /app/build/libs/*.jar app.jar
            RUN addgroup -S appgroup && adduser -S appuser -G appgroup
            USER appuser
            EXPOSE 8080
            ENTRYPOINT ["java", "-jar", "app.jar"]
        """),
    }


# ---------------------------------------------------------------------------
# Shared / root files
# ---------------------------------------------------------------------------


def _docker_compose(backend: str) -> str:
    """Generate docker-compose.yml."""
    backend_build = "backend"
    backend_cmd = {
        "express": '    command: npx tsx watch src/app.ts\n    working_dir: /app\n',
        "fastapi": '    command: uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload\n',
        "spring": '    command: ./gradlew bootRun\n',
    }[backend]

    return dedent(f"""\
        services:
          frontend:
            build:
              context: ./frontend
              dockerfile: Dockerfile
            ports:
              - "3000:3000"
            volumes:
              - ./frontend/src:/app/src
            depends_on:
              - api

          api:
            build:
              context: ./{backend_build}
            ports:
              - "8080:8080"
        {backend_cmd}    environment:
              DATABASE_URL: postgresql://myapp:localdev@postgres:5432/myapp_dev
              JWT_SECRET: local-dev-secret-change-in-production-32chars
              CORS_ORIGIN: http://localhost:3000
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
              POSTGRES_DB: myapp_dev
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
    """)


def _env_example(backend: str) -> str:
    """Generate .env.example."""
    common = dedent("""\
        # Database
        DATABASE_URL=postgresql://myapp:localdev@localhost:5432/myapp_dev
        DB_USER=myapp
        DB_PASSWORD=localdev

        # Auth
        JWT_SECRET=change-me-in-production-use-a-long-random-string-here

        # CORS
        CORS_ORIGIN=http://localhost:3000

        # Redis
        REDIS_URL=redis://localhost:6379
    """)
    if backend == "express":
        common += "\n# Express\nNODE_ENV=development\nPORT=8080\n"
    elif backend == "fastapi":
        common += "\n# FastAPI\nAPP_ENV=development\n"
    elif backend == "spring":
        common += "\n# Spring\nSPRING_PROFILES_ACTIVE=dev\n"
    return common


def _gitignore() -> str:
    return dedent("""\
        # Dependencies
        node_modules/
        .pnpm-store/
        __pycache__/
        *.py[cod]
        .venv/
        venv/
        .gradle/
        build/
        target/

        # Build output
        dist/
        .next/
        out/

        # Environment
        .env
        .env.local
        .env.*.local

        # IDE
        .idea/
        *.iml
        .vscode/settings.json
        *.swp

        # OS
        .DS_Store
        Thumbs.db

        # Testing
        coverage/
        .pytest_cache/
        htmlcov/
        test-results/

        # Logs
        *.log
    """)


def _editorconfig() -> str:
    return dedent("""\
        root = true

        [*]
        charset = utf-8
        end_of_line = lf
        insert_final_newline = true
        trim_trailing_whitespace = true
        indent_style = space
        indent_size = 2

        [*.py]
        indent_size = 4

        [*.java]
        indent_size = 4

        [Makefile]
        indent_style = tab

        [*.md]
        trim_trailing_whitespace = false
    """)


def _ci_workflow(name: str, frontend: str, backend: str) -> str:
    """Generate .github/workflows/ci.yml."""
    backend_steps = {
        "express": dedent("""\
              - uses: actions/setup-node@v4
                with:
                  node-version: 20
              - run: cd backend && npm ci
              - run: cd backend && npm run lint
              - run: cd backend && npm run typecheck
              - run: cd backend && npm test
        """),
        "fastapi": dedent("""\
              - uses: actions/setup-python@v5
                with:
                  python-version: "3.12"
              - run: pip install -e "backend/.[dev]"
              - run: cd backend && ruff check .
              - run: cd backend && mypy .
              - run: cd backend && pytest
        """),
        "spring": dedent("""\
              - uses: actions/setup-java@v4
                with:
                  distribution: temurin
                  java-version: 21
              - run: cd backend && ./gradlew check
        """),
    }

    return dedent(f"""\
        name: CI

        on:
          push:
            branches: [main]
          pull_request:
            branches: [main]

        jobs:
          frontend:
            runs-on: ubuntu-latest
            steps:
              - uses: actions/checkout@v4
              - uses: actions/setup-node@v4
                with:
                  node-version: 20
              - run: cd frontend && npm ci
              - run: cd frontend && npm run lint
              - run: cd frontend && npm run typecheck
              - run: cd frontend && npm run build

          backend:
            runs-on: ubuntu-latest
            services:
              postgres:
                image: postgres:16-alpine
                env:
                  POSTGRES_DB: myapp_test
                  POSTGRES_USER: myapp
                  POSTGRES_PASSWORD: testpass
                ports:
                  - 5432:5432
                options: >-
                  --health-cmd "pg_isready -U myapp"
                  --health-interval 5s
                  --health-timeout 5s
                  --health-retries 5
            env:
              DATABASE_URL: postgresql://myapp:testpass@localhost:5432/myapp_test
              JWT_SECRET: test-secret-for-ci-minimum-32-characters-long
            steps:
              - uses: actions/checkout@v4
        {backend_steps[backend]}
    """)


def _readme(name: str, frontend: str, backend: str) -> str:
    return dedent(f"""\
        # {name}

        Full-stack application: {frontend} + {backend}

        ## Prerequisites

        - Node.js 20+ (via nvm)
        - {"Python 3.12+ (via uv)" if backend == "fastapi" else "Java 21+ (via SDKMAN!)" if backend == "spring" else ""}
        - Docker and Docker Compose

        ## Quick Start

        ```bash
        # Clone and enter directory
        git clone <repo-url>
        cd {name}

        # Start infrastructure
        docker compose up -d postgres redis

        # Set up environment
        cp .env.example .env

        # Backend
        cd backend
        {"npm install && npm run db:migrate && npm run dev" if backend == "express" else "uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload --port 8080" if backend == "fastapi" else "./gradlew bootRun"}

        # Frontend (in a new terminal)
        cd frontend
        npm install && npm run dev
        ```

        Open http://localhost:3000 in your browser.

        ## Project Structure

        ```
        {name}/
          frontend/       # {frontend.title()} frontend
          backend/        # {backend.title()} backend
          docker-compose.yml
          .github/workflows/ci.yml
        ```

        ## Available Commands

        | Command | Description |
        |---|---|
        | `docker compose up -d` | Start all services |
        | `docker compose down` | Stop all services |
        | `cd frontend && npm run dev` | Start frontend dev server |
        | `cd backend && {"npm run dev" if backend == "express" else "uv run uvicorn app.main:app --reload" if backend == "fastapi" else "./gradlew bootRun"}` | Start backend dev server |
    """)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def scaffold_project(
    name: str,
    frontend: str,
    backend: str,
    output_dir: Path,
) -> Path:
    """Generate a full-stack project skeleton.

    Args:
        name: Project name (used as directory name).
        frontend: Frontend framework (react, next).
        backend: Backend framework (express, fastapi, spring).
        output_dir: Parent directory for the project.

    Returns:
        Path to the generated project root.
    """
    project_dir = output_dir / name
    if project_dir.exists():
        print(f"Error: Directory already exists: {project_dir}", file=sys.stderr)
        sys.exit(1)

    # Collect all files
    files: dict[str, str] = {}

    # Frontend
    if frontend == "react":
        files.update(_react_files(name))
    elif frontend == "next":
        files.update(_next_files(name))

    # Backend
    if backend == "express":
        files.update(_express_files(name))
    elif backend == "fastapi":
        files.update(_fastapi_files(name))
    elif backend == "spring":
        files.update(_spring_files(name))

    # Root files
    files["docker-compose.yml"] = _docker_compose(backend)
    files[".env.example"] = _env_example(backend)
    files[".gitignore"] = _gitignore()
    files[".editorconfig"] = _editorconfig()
    files[".github/workflows/ci.yml"] = _ci_workflow(name, frontend, backend)
    files["README.md"] = _readme(name, frontend, backend)

    # Write files
    for relative_path, content in files.items():
        file_path = project_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    print(f"Project scaffolded at: {project_dir}")
    print(f"  Frontend: {frontend}")
    print(f"  Backend:  {backend}")
    print(f"  Files:    {len(files)}")
    print()
    print("Next steps:")
    print(f"  cd {project_dir}")
    print(f"  cp .env.example .env")
    print(f"  docker compose up -d postgres redis")
    print(f"  cd frontend && npm install && npm run dev")
    if backend == "express":
        print(f"  cd backend && npm install && npm run dev")
    elif backend == "fastapi":
        print(f"  cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8080")
    elif backend == "spring":
        print(f"  cd backend && ./gradlew bootRun")

    return project_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a full-stack project skeleton.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--name", "-n", required=True, help="Project name.")
    parser.add_argument(
        "--frontend", "-f",
        required=True,
        choices=FRONTEND_CHOICES,
        help="Frontend framework.",
    )
    parser.add_argument(
        "--backend", "-b",
        required=True,
        choices=BACKEND_CHOICES,
        help="Backend framework.",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=".",
        help="Parent directory for the generated project (default: cwd).",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()

    if not output_dir.exists():
        print(f"Error: Output directory does not exist: {output_dir}", file=sys.stderr)
        sys.exit(1)

    scaffold_project(
        name=args.name,
        frontend=args.frontend,
        backend=args.backend,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
