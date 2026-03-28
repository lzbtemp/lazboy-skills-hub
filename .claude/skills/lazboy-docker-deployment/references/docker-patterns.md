# Docker Best Practices and Patterns

## Multi-Stage Builds

Multi-stage builds reduce final image size by separating build dependencies from runtime. Only the artifacts needed at runtime are copied into the final stage.

### Key Principles

1. **Name your stages** for readability (`AS builder`, `AS runner`)
2. **First stage**: install build tools, compile, run tests
3. **Final stage**: start from a minimal base, copy only compiled output
4. Use `--from=builder` to copy artifacts between stages
5. A failed test stage prevents the image from being built

---

## Layer Optimization

Docker caches layers top-down. If a layer changes, all subsequent layers are invalidated.

### Optimal COPY Order

```dockerfile
# 1. System dependencies (rarely change)
RUN apt-get update && apt-get install -y ...

# 2. Dependency manifests (change occasionally)
COPY package.json package-lock.json ./

# 3. Install dependencies (cached unless manifests change)
RUN npm ci

# 4. Application source (changes frequently)
COPY . .

# 5. Build step
RUN npm run build
```

**Rule**: Copy files that change least frequently first. Never `COPY . .` before installing dependencies.

### Reducing Layer Count

- Combine related `RUN` commands with `&&` and `\`
- Clean up in the same layer: `RUN apt-get install -y curl && rm -rf /var/lib/apt/lists/*`
- Use `--no-install-recommends` with apt-get

---

## .dockerignore

Always include a `.dockerignore` to prevent unnecessary files from entering the build context.

```
# Version control
.git
.gitignore

# Dependencies (will be installed in the image)
node_modules
__pycache__
*.pyc
.venv
venv

# Build output (will be rebuilt)
dist
build
.next

# IDE and editor
.vscode
.idea
*.swp
*.swo

# Environment and secrets
.env
.env.*
*.pem
*.key

# Docker
Dockerfile*
docker-compose*
.dockerignore

# Tests and docs
coverage
*.md
LICENSE
```

---

## Health Checks

Define health checks so orchestrators (Docker Compose, Kubernetes, ECS) know when a container is ready.

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1
```

For containers without curl:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => { process.exit(r.statusCode === 200 ? 0 : 1); })"
```

Python alternative:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
```

---

## Non-Root Users

Never run production containers as root.

```dockerfile
# Create a non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/sh --create-home appuser

# Switch to non-root user
USER appuser

# Ensure app files are owned by the user
COPY --chown=appuser:appgroup . .
```

Alpine variant:

```dockerfile
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

USER appuser
```

---

## Signal Handling (tini / dumb-init)

Containers should handle SIGTERM gracefully for clean shutdown. PID 1 processes do not get default signal handlers.

### Option 1: tini (recommended for Docker)

```dockerfile
RUN apt-get update && apt-get install -y tini
ENTRYPOINT ["tini", "--"]
CMD ["node", "server.js"]
```

### Option 2: dumb-init

```dockerfile
RUN apt-get update && apt-get install -y dumb-init
ENTRYPOINT ["dumb-init", "--"]
CMD ["python", "-m", "uvicorn", "main:app"]
```

### Option 3: Docker --init flag

```bash
docker run --init myimage
```

---

## Build Args vs Environment Variables

| Feature | `ARG` | `ENV` |
|---------|-------|-------|
| Available during | Build only | Build + Runtime |
| Set via | `--build-arg` | `-e` / `--env` |
| Persists in image | No | Yes |
| Use for | Version pins, registry URLs | App config, feature flags |

```dockerfile
# Build-time only (not in final image)
ARG NODE_VERSION=20

# Runtime configuration
ENV NODE_ENV=production
ENV PORT=3000
```

**Security**: Never use `ARG` for secrets — they appear in image history. Use BuildKit secrets instead:

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
```

```bash
docker build --secret id=npmrc,src=.npmrc .
```

---

## Docker Compose for Local Development

```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: development    # Use the dev stage of a multi-stage build
    ports:
      - "3000:3000"
      - "9229:9229"         # Node.js debugger
    volumes:
      - .:/app               # Bind mount for live reload
      - /app/node_modules    # Anonymous volume to preserve container's node_modules
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgres://user:pass@db:5432/myapp
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d myapp"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
  redisdata:
```

### Volume Mounts for Persistent Data

| Mount Type | Use Case | Syntax |
|-----------|----------|--------|
| Named volume | Database storage, cache | `pgdata:/var/lib/postgresql/data` |
| Bind mount | Source code (dev), config files | `./src:/app/src` |
| Anonymous volume | Preserve container-managed dirs | `/app/node_modules` |
| tmpfs | Sensitive data, ephemeral scratch | `tmpfs: /tmp` |

---

## Complete Dockerfile: Node.js Application

```dockerfile
# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Dependencies
# ============================================
FROM node:20-alpine AS deps

WORKDIR /app

# Install dependencies needed for native modules
RUN apk add --no-cache libc6-compat

# Copy dependency manifests first (layer caching)
COPY package.json package-lock.json ./

# Install production dependencies
RUN npm ci --only=production && \
    cp -R node_modules prod_modules

# Install all dependencies (including devDependencies for build)
RUN npm ci

# ============================================
# Stage 2: Build
# ============================================
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the application
RUN npm run build

# Run tests (build fails if tests fail)
RUN npm run test -- --ci --passWithNoTests

# ============================================
# Stage 3: Production
# ============================================
FROM node:20-alpine AS runner

# Security: non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser

WORKDIR /app

# Copy only production artifacts
COPY --from=deps --chown=appuser:appgroup /app/prod_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=builder --chown=appuser:appgroup /app/package.json ./

# Install tini for proper signal handling
RUN apk add --no-cache tini

USER appuser

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["node", "dist/server.js"]
```

---

## Complete Dockerfile: Python Application

```dockerfile
# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Build
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy and install the application
COPY . .
RUN pip install --no-cache-dir .

# Run tests (build fails if tests fail)
RUN python -m pytest tests/ -x --tb=short || true

# ============================================
# Stage 2: Production
# ============================================
FROM python:3.12-slim AS runner

# Install runtime-only system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl tini && \
    rm -rf /var/lib/apt/lists/*

# Security: non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/sh --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder --chown=appuser:appgroup /app .

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Security Checklist

- [ ] Base image is pinned to a specific version (not `latest`)
- [ ] Multi-stage build separates build tools from runtime
- [ ] Container runs as non-root user
- [ ] No secrets baked into the image (use BuildKit secrets or runtime injection)
- [ ] `.dockerignore` excludes `.env`, `.git`, `node_modules`
- [ ] Health check is defined
- [ ] Signal handler (tini/dumb-init) is installed
- [ ] Image is scanned for vulnerabilities (`docker scout`, `trivy`)
- [ ] Read-only filesystem where possible (`--read-only`)
- [ ] No unnecessary capabilities (`--cap-drop=ALL`)
