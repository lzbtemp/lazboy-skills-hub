---
name: lazboy-ci-cd-pipeline
description: "Set up and maintain CI/CD pipelines for La-Z-Boy applications using GitHub Actions. Covers build, test, lint, security scan, Docker image creation, and deployment to Azure. Use when configuring automated pipelines or troubleshooting build failures."
version: "1.0.0"
category: DevOps
tags: [devops, ci-cd, github-actions, docker]
---

# La-Z-Boy CI/CD Pipeline Skill

Standards for building CI/CD pipelines at La-Z-Boy using GitHub Actions.

**Reference files — load when needed:**
- `references/pipeline-templates.md` — reusable workflow templates
- `references/environment-matrix.md` — deployment environment configurations

**Scripts — run when needed:**
- `scripts/setup_pipeline.py` — generate GitHub Actions workflow for a project
- `scripts/check_pipeline.py` — validate workflow YAML syntax

---

## 1. Pipeline Stages

```
Commit → Lint → Test → Build → Security Scan → Deploy (Staging) → Deploy (Production)
```

## 2. Standard GitHub Actions Workflow

```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npm run lint
      - run: npm run type-check

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  security:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - run: npm audit --audit-level=high
      - uses: github/codeql-action/analyze@v3

  deploy-staging:
    runs-on: ubuntu-latest
    needs: [build, security]
    if: github.ref == 'refs/heads/develop'
    environment: staging
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist }
      - run: echo "Deploy to staging..."

  deploy-production:
    runs-on: ubuntu-latest
    needs: [build, security]
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist }
      - run: echo "Deploy to production..."
```

## 3. Docker Build Standards

```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --production=false
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
RUN addgroup -g 1001 -S app && adduser -S app -u 1001
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER app
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

## 4. Environment Strategy

| Environment | Branch | Auto-deploy | Approval |
|---|---|---|---|
| Development | feature/* | No | None |
| Staging | develop | Yes | None |
| Production | main | Yes | Required |

## 5. Pipeline Rules

- All PRs must pass CI before merge
- Test coverage must not decrease
- No high/critical vulnerabilities in dependencies
- Docker images must use non-root user
- Secrets managed via GitHub Secrets, never in code
