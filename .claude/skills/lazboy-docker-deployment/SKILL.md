---
name: lazboy-docker-deployment
description: "Containerize and deploy La-Z-Boy applications using Docker and Kubernetes. Covers Dockerfile best practices, docker-compose for local development, Kubernetes manifests, health checks, and monitoring. Use when containerizing applications or managing deployments."
version: "1.0.0"
category: DevOps
tags: [devops, docker, kubernetes, deployment]
---

# La-Z-Boy Docker & Deployment Skill

Standards for containerizing and deploying La-Z-Boy applications.

**Reference files — load when needed:**
- `references/docker-patterns.md` — approved Dockerfile patterns
- `references/k8s-manifests.md` — Kubernetes manifest templates

**Scripts — run when needed:**
- `scripts/generate_dockerfile.py` — create optimized Dockerfile for a project
- `scripts/health_check.py` — verify deployment health across environments

---

## 1. Dockerfile Best Practices

- Use specific base image tags (not `latest`)
- Multi-stage builds to minimize image size
- Run as non-root user
- Use `.dockerignore` to exclude unnecessary files
- Order layers from least to most frequently changed
- Pin dependency versions

### Image Size Targets
| App Type | Max Image Size |
|---|---|
| Node.js API | 150 MB |
| Python API | 200 MB |
| Static frontend | 50 MB |

## 2. Docker Compose for Local Dev

```yaml
version: "3.8"
services:
  app:
    build: .
    ports: ["3000:3000"]
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/app
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_started }
    volumes:
      - ./src:/app/src

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d app"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

## 3. Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  labels:
    app: lazboy-app
spec:
  replicas: 3
  selector:
    matchLabels: { app: lazboy-app }
  template:
    spec:
      containers:
        - name: app
          image: lazboy/app:1.0.0
          ports: [{ containerPort: 3000 }]
          resources:
            requests: { cpu: "100m", memory: "128Mi" }
            limits: { cpu: "500m", memory: "512Mi" }
          livenessProbe:
            httpGet: { path: /health, port: 3000 }
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet: { path: /ready, port: 3000 }
            initialDelaySeconds: 5
            periodSeconds: 10
```

## 4. Health Check Endpoints

Every service must expose:
- `GET /health` — returns 200 if process is running
- `GET /ready` — returns 200 if all dependencies are connected

## 5. Deployment Checklist

- [ ] Docker image builds successfully
- [ ] Image scanned for vulnerabilities (Trivy/Snyk)
- [ ] Health checks configured and passing
- [ ] Resource limits set appropriately
- [ ] Secrets managed via K8s secrets or vault
- [ ] Horizontal pod autoscaler configured
- [ ] Rollback strategy tested
