# Development Environment Setup Guide

## Overview

This guide covers setting up a complete development environment for full-stack projects. It includes version managers, editors, linters, formatters, and Git hooks to ensure consistent tooling across team members.

---

## 1. Node.js with nvm

### Installation

```bash
# macOS / Linux
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# Verify installation (restart terminal first)
nvm --version
```

### Usage

```bash
# Install the latest LTS version
nvm install --lts

# Install a specific version
nvm install 20.11.0

# Use a specific version
nvm use 20

# Set default version
nvm alias default 20

# Create .nvmrc for the project
echo "20" > .nvmrc

# Auto-use the version specified in .nvmrc
nvm use  # reads .nvmrc in current directory
```

### Automatic Version Switching (zsh)

Add to `~/.zshrc`:

```bash
# Automatically call nvm use when entering a directory with .nvmrc
autoload -U add-zsh-hook
load-nvmrc() {
  local nvmrc_path
  nvmrc_path="$(nvm_find_nvmrc)"
  if [ -n "$nvmrc_path" ]; then
    local nvmrc_node_version
    nvmrc_node_version=$(nvm version "$(cat "${nvmrc_path}")")
    if [ "$nvmrc_node_version" = "N/A" ]; then
      nvm install
    elif [ "$nvmrc_node_version" != "$(nvm version)" ]; then
      nvm use
    fi
  fi
}
add-zsh-hook chpwd load-nvmrc
load-nvmrc
```

### Package Manager: pnpm (Recommended for Monorepos)

```bash
# Install pnpm via corepack (bundled with Node.js)
corepack enable
corepack prepare pnpm@latest --activate

# Verify
pnpm --version
```

---

## 2. Python with uv (Recommended) or pyenv

### Option A: uv (Fast, Modern)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify
uv --version
```

```bash
# Create a project with a specific Python version
uv init my-project --python 3.12
cd my-project

# Install dependencies
uv add fastapi uvicorn pydantic-settings
uv add --dev pytest ruff mypy

# Run commands in the virtual environment
uv run python main.py
uv run pytest

# Lock and sync dependencies
uv lock
uv sync
```

### Option B: pyenv

```bash
# macOS (Homebrew)
brew install pyenv pyenv-virtualenv

# Linux
curl https://pyenv.run | bash
```

Add to `~/.zshrc` or `~/.bashrc`:

```bash
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

```bash
# Install a Python version
pyenv install 3.12.2

# Set global default
pyenv global 3.12.2

# Set project-local version (creates .python-version)
pyenv local 3.12.2

# Create virtual environment
pyenv virtualenv 3.12.2 my-project-env
pyenv activate my-project-env
```

---

## 3. Java with SDKMAN!

### Installation

```bash
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk version
```

### Usage

```bash
# List available Java versions
sdk list java

# Install a specific version
sdk install java 21.0.2-tem    # Temurin (Eclipse Adoptium)
sdk install java 21.0.2-graal  # GraalVM

# Use a version
sdk use java 21.0.2-tem

# Set default
sdk default java 21.0.2-tem

# Install build tools
sdk install gradle 8.5
sdk install maven 3.9.6

# Project-level version pinning
sdk env init  # Creates .sdkmanrc
```

**.sdkmanrc** example:

```properties
java=21.0.2-tem
gradle=8.5
```

---

## 4. Docker

### Installation

```bash
# macOS: Install Docker Desktop
brew install --cask docker

# Linux (Ubuntu/Debian): Install Docker Engine
# See https://docs.docker.com/engine/install/ubuntu/
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### Docker Compose for Development Databases

```yaml
# docker-compose.dev.yml
services:
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
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myapp"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  mailpit:
    image: axllent/mailpit:latest
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web UI
    environment:
      MP_SMTP_AUTH_ACCEPT_ANY: 1
      MP_SMTP_AUTH_ALLOW_INSECURE: 1

volumes:
  pgdata:
```

```bash
# Start services
docker compose -f docker-compose.dev.yml up -d

# Stop services
docker compose -f docker-compose.dev.yml down

# Stop and remove volumes
docker compose -f docker-compose.dev.yml down -v
```

---

## 5. PostgreSQL via Docker

### Quick Setup

```bash
# Start PostgreSQL
docker run -d \
  --name postgres-dev \
  -e POSTGRES_DB=myapp_dev \
  -e POSTGRES_USER=myapp \
  -e POSTGRES_PASSWORD=localdev \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16-alpine

# Connect with psql
docker exec -it postgres-dev psql -U myapp -d myapp_dev

# Stop
docker stop postgres-dev

# Remove
docker rm postgres-dev
```

### Database Client Tools

```bash
# psql (CLI)
brew install libpq
brew link --force libpq

# pgcli (enhanced CLI with autocomplete)
pip install pgcli
pgcli postgresql://myapp:localdev@localhost:5432/myapp_dev
```

---

## 6. VS Code Extensions

### Essential Extensions

Create `.vscode/extensions.json` in your project root:

```json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "redhat.java",
    "vscjava.vscode-spring-boot-dashboard",
    "prisma.prisma",
    "ms-azuretools.vscode-docker",
    "eamodio.gitlens",
    "usernamehw.errorlens",
    "streetsidesoftware.code-spell-checker",
    "vitest.explorer",
    "ms-playwright.playwright"
  ]
}
```

### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit",
    "source.organizeImports": "explicit"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "[java]": {
    "editor.defaultFormatter": "redhat.java"
  },
  "typescript.preferences.importModuleSpecifier": "non-relative",
  "files.exclude": {
    "**/.git": true,
    "**/node_modules": true,
    "**/__pycache__": true,
    "**/.pytest_cache": true
  },
  "search.exclude": {
    "**/node_modules": true,
    "**/dist": true,
    "**/.next": true
  }
}
```

---

## 7. ESLint Configuration

### Flat Config (eslint.config.js) - ESLint 9+

```javascript
// eslint.config.js
import js from "@eslint/js";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import importPlugin from "eslint-plugin-import";

export default [
  js.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: "./tsconfig.json",
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      react: reactPlugin,
      "react-hooks": reactHooksPlugin,
      import: importPlugin,
    },
    rules: {
      // TypeScript
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/consistent-type-imports": "error",

      // React
      "react/react-in-jsx-scope": "off",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",

      // Imports
      "import/order": [
        "error",
        {
          groups: [
            "builtin",
            "external",
            "internal",
            "parent",
            "sibling",
            "index",
          ],
          "newlines-between": "always",
          alphabetize: { order: "asc" },
        },
      ],
    },
    settings: {
      react: { version: "detect" },
    },
  },
  {
    ignores: ["dist/", "node_modules/", ".next/", "coverage/"],
  },
];
```

---

## 8. Prettier Configuration

### .prettierrc

```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf",
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

### .prettierignore

```
dist/
build/
node_modules/
.next/
coverage/
pnpm-lock.yaml
package-lock.json
*.min.js
```

---

## 9. Pre-commit Hooks

### Husky + lint-staged (JavaScript/TypeScript)

```bash
# Install
pnpm add -D husky lint-staged

# Initialize husky
pnpm exec husky init
```

**package.json** additions:

```json
{
  "scripts": {
    "prepare": "husky"
  },
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{json,md,yml,yaml}": [
      "prettier --write"
    ],
    "*.{css,scss}": [
      "prettier --write"
    ]
  }
}
```

**.husky/pre-commit**:

```bash
pnpm exec lint-staged
```

**.husky/commit-msg**:

```bash
pnpm exec commitlint --edit $1
```

### Commitlint Configuration

```bash
pnpm add -D @commitlint/cli @commitlint/config-conventional
```

**commitlint.config.js**:

```javascript
export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "build",
        "ci",
        "chore",
        "revert",
      ],
    ],
    "subject-max-length": [2, "always", 72],
  },
};
```

### pre-commit (Python)

```bash
pip install pre-commit
```

**.pre-commit-config.yaml**:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ["--maxkb=500"]
      - id: detect-private-key
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.0]
```

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Update hook versions
pre-commit autoupdate
```

---

## 10. EditorConfig

Create `.editorconfig` in the project root:

```ini
# EditorConfig: https://editorconfig.org
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

[*.{go,rs}]
indent_style = tab

[Makefile]
indent_style = tab

[*.md]
trim_trailing_whitespace = false

[*.{yml,yaml}]
indent_size = 2

[docker-compose*.yml]
indent_size = 2
```

---

## 11. Git Configuration

### .gitignore (Comprehensive)

```gitignore
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
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
coverage/
.pytest_cache/
htmlcov/
.nyc_output/
test-results/

# Logs
*.log
logs/

# Docker
docker-compose.override.yml
```

### .gitattributes

```gitattributes
# Normalize line endings
* text=auto eol=lf

# Binary files
*.png binary
*.jpg binary
*.gif binary
*.ico binary
*.woff binary
*.woff2 binary

# Lock files - don't diff
pnpm-lock.yaml -diff
package-lock.json -diff

# Linguist overrides
*.min.js linguist-generated
dist/** linguist-generated
```

---

## 12. Makefile for Common Tasks

```makefile
.PHONY: help setup dev test lint build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial project setup
	cp -n .env.example .env || true
	docker compose -f docker-compose.dev.yml up -d
	pnpm install
	pnpm exec prisma migrate dev
	pnpm exec prisma db seed

dev: ## Start development servers
	docker compose -f docker-compose.dev.yml up -d
	pnpm turbo run dev

test: ## Run all tests
	pnpm turbo run test

lint: ## Run linters
	pnpm turbo run lint typecheck

build: ## Build all packages
	pnpm turbo run build

clean: ## Clean build artifacts and dependencies
	rm -rf node_modules .turbo
	find . -name 'node_modules' -type d -prune -exec rm -rf {} +
	find . -name 'dist' -type d -prune -exec rm -rf {} +
	find . -name '.next' -type d -prune -exec rm -rf {} +
	docker compose -f docker-compose.dev.yml down -v
```

---

## Quick Reference: New Developer Onboarding Checklist

```markdown
1. [ ] Install Homebrew (macOS) or system package manager
2. [ ] Install nvm and Node.js LTS
3. [ ] Enable corepack and install pnpm
4. [ ] Install uv (or pyenv) and Python 3.12+
5. [ ] Install SDKMAN! and Java 21 (if needed)
6. [ ] Install Docker Desktop
7. [ ] Install VS Code with recommended extensions
8. [ ] Clone the repository
9. [ ] Run `make setup` (or follow README)
10. [ ] Verify with `make test`
```
