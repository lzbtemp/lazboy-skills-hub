# Pipeline Templates

GitHub Actions workflow templates for common project types.

---

## Node.js / React Application

Full CI/CD pipeline: lint, test, build, deploy to AWS S3 + CloudFront.

```yaml
name: Node.js CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  id-token: write

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  NODE_VERSION: "20"

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: "npm"

      - run: npm ci

      - run: npm run lint

      - run: npx tsc --noEmit

  test:
    name: Test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: "npm"

      - run: npm ci

      - run: npm test -- --coverage --ci
        env:
          CI: true

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: coverage/
          retention-days: 7

  build:
    name: Build
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: test
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: "npm"

      - run: npm ci

      - run: npm run build
        env:
          REACT_APP_API_URL: ${{ vars.API_URL }}

      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: build/
          retention-days: 1

  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: build
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: build/

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-arn: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Deploy to S3
        run: aws s3 sync build/ s3://${{ vars.S3_BUCKET }} --delete

      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ vars.CLOUDFRONT_DIST_ID }} \
            --paths "/*"
```

---

## Python Application

CI/CD with ruff linting, pytest, Docker build, and push to ECR.

```yaml
name: Python CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  id-token: write
  packages: write

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  PYTHON_VERSION: "3.12"
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy
          pip install -r requirements.txt

      - name: Ruff check
        run: ruff check .

      - name: Ruff format check
        run: ruff format --check .

      - name: Type check
        run: mypy src/ --ignore-missing-imports

  test:
    name: Test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest tests/ \
            --cov=src \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=report.xml \
            -v
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: |
            report.xml
            coverage.xml
          retention-days: 7

  build-and-push:
    name: Build & Push Docker Image
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=raw,value=latest

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: build-and-push
    environment: production
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-arn: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster ${{ vars.ECS_CLUSTER }} \
            --service ${{ vars.ECS_SERVICE }} \
            --force-new-deployment
```

---

## Docker Multi-Stage Build

Optimized Dockerfile for Node.js and Python with multi-stage builds.

### Node.js Multi-Stage

```yaml
# .github/workflows/docker-build.yml
name: Docker Build

on:
  push:
    branches: [main]
    paths:
      - "Dockerfile"
      - "src/**"
      - "package*.json"

permissions:
  contents: read
  packages: write

jobs:
  build:
    name: Build & Push
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            NODE_ENV=production

      - name: Run Trivy vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          format: "sarif"
          output: "trivy-results.sarif"
          severity: "CRITICAL,HIGH"

      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: "trivy-results.sarif"
```

### Reference Dockerfile (Node.js)

```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production && \
    cp -R node_modules /prod_modules && \
    npm ci

# Stage 2: Build
FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: Production
FROM node:20-alpine AS production
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup
WORKDIR /app
COPY --from=deps /prod_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/index.js"]
```

### Reference Dockerfile (Python)

```dockerfile
# Stage 1: Build
FROM python:3.12-slim AS build
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.12-slim AS production
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY src/ ./src/
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Terraform Infrastructure

CI/CD for Terraform with plan on PR, apply on merge.

```yaml
name: Terraform

on:
  push:
    branches: [main]
    paths:
      - "infra/**"
  pull_request:
    branches: [main]
    paths:
      - "infra/**"

permissions:
  contents: read
  pull-requests: write
  id-token: write

env:
  TF_VERSION: "1.7"
  TF_WORKING_DIR: infra
  TF_VAR_environment: production

jobs:
  validate:
    name: Validate
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: ${{ env.TF_WORKING_DIR }}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform fmt
        run: terraform fmt -check -recursive

      - name: Terraform init
        run: terraform init -backend=false

      - name: Terraform validate
        run: terraform validate

      - name: TFLint
        uses: terraform-linters/setup-tflint@v4
      - run: tflint --init && tflint

  plan:
    name: Plan
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: validate
    defaults:
      run:
        working-directory: ${{ env.TF_WORKING_DIR }}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-arn: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Terraform init
        run: terraform init

      - name: Terraform plan
        id: plan
        run: terraform plan -no-color -out=tfplan
        continue-on-error: true

      - name: Comment PR with plan
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const plan = `${{ steps.plan.outputs.stdout }}`;
            const truncated = plan.length > 60000
              ? plan.substring(0, 60000) + "\n\n... (truncated)"
              : plan;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `#### Terraform Plan\n\`\`\`\n${truncated}\n\`\`\``
            });

      - name: Fail on plan error
        if: steps.plan.outcome == 'failure'
        run: exit 1

      - uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: ${{ env.TF_WORKING_DIR }}/tfplan
          retention-days: 1

  apply:
    name: Apply
    runs-on: ubuntu-latest
    timeout-minutes: 30
    needs: plan
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production
    defaults:
      run:
        working-directory: ${{ env.TF_WORKING_DIR }}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-arn: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Terraform init
        run: terraform init

      - uses: actions/download-artifact@v4
        with:
          name: tfplan
          path: ${{ env.TF_WORKING_DIR }}

      - name: Terraform apply
        run: terraform apply -auto-approve tfplan
```

---

## Reusable Workflow (Callable)

A reusable workflow that other repos can call for standard Node.js CI.

```yaml
# .github/workflows/reusable-node-ci.yml
name: Reusable Node.js CI

on:
  workflow_call:
    inputs:
      node-version:
        description: "Node.js version"
        required: false
        type: string
        default: "20"
      working-directory:
        description: "Working directory"
        required: false
        type: string
        default: "."
    secrets:
      NPM_TOKEN:
        required: false

jobs:
  ci:
    name: CI
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: ${{ inputs.working-directory }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: "npm"
          cache-dependency-path: ${{ inputs.working-directory }}/package-lock.json

      - run: npm ci
        env:
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}

      - run: npm run lint --if-present

      - run: npm test --if-present

      - run: npm run build --if-present
```

### Caller example

```yaml
# In another repository
name: CI
on: [push, pull_request]
jobs:
  ci:
    uses: your-org/.github/.github/workflows/reusable-node-ci.yml@main
    with:
      node-version: "20"
    secrets:
      NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```
