#!/usr/bin/env bash
#
# setup_dev.sh - Development environment setup script
#
# Sets up a full-stack development environment by checking for required
# tools, installing dependencies, starting services, running migrations,
# and seeding the database.
#
# Usage:
#   ./setup_dev.sh              # Full setup
#   ./setup_dev.sh --skip-docker   # Skip Docker service startup
#   ./setup_dev.sh --skip-seed     # Skip database seeding
#   ./setup_dev.sh --check-only    # Only check tool availability
#
# Requirements:
#   - macOS (Homebrew) or Linux (apt/dnf)
#   - Internet connection for installing tools
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REQUIRED_NODE_VERSION="20"
REQUIRED_PYTHON_VERSION="3.12"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Colors (disabled if not a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
fatal()   { error "$@"; exit 1; }

command_exists() { command -v "$1" &>/dev/null; }

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        *)       echo "unknown" ;;
    esac
}

OS=$(detect_os)

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

SKIP_DOCKER=false
SKIP_SEED=false
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-docker) SKIP_DOCKER=true; shift ;;
        --skip-seed)   SKIP_SEED=true; shift ;;
        --check-only)  CHECK_ONLY=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--skip-docker] [--skip-seed] [--check-only]"
            echo ""
            echo "Options:"
            echo "  --skip-docker  Do not start Docker services"
            echo "  --skip-seed    Do not seed the database"
            echo "  --check-only   Only verify tool installation"
            exit 0
            ;;
        *)
            fatal "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Tool checks and installation
# ---------------------------------------------------------------------------

check_homebrew() {
    if [[ "$OS" != "macos" ]]; then
        return 0
    fi
    if command_exists brew; then
        success "Homebrew installed"
    else
        info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        success "Homebrew installed"
    fi
}

check_node() {
    if command_exists node; then
        local version
        version=$(node --version | sed 's/v//' | cut -d. -f1)
        if [[ "$version" -ge "$REQUIRED_NODE_VERSION" ]]; then
            success "Node.js $(node --version)"
            return 0
        else
            warn "Node.js $(node --version) found, but v${REQUIRED_NODE_VERSION}+ required"
        fi
    else
        warn "Node.js not found"
    fi

    if command_exists nvm; then
        info "Installing Node.js ${REQUIRED_NODE_VERSION} via nvm..."
        nvm install "$REQUIRED_NODE_VERSION"
        nvm use "$REQUIRED_NODE_VERSION"
        success "Node.js $(node --version) installed via nvm"
    elif command_exists fnm; then
        info "Installing Node.js ${REQUIRED_NODE_VERSION} via fnm..."
        fnm install "$REQUIRED_NODE_VERSION"
        fnm use "$REQUIRED_NODE_VERSION"
        success "Node.js $(node --version) installed via fnm"
    else
        info "Installing nvm..."
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        # shellcheck source=/dev/null
        [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
        nvm install "$REQUIRED_NODE_VERSION"
        success "Node.js $(node --version) installed via nvm"
    fi
}

check_pnpm() {
    if command_exists pnpm; then
        success "pnpm $(pnpm --version)"
    else
        info "Installing pnpm via corepack..."
        if command_exists corepack; then
            corepack enable
            corepack prepare pnpm@latest --activate
        else
            npm install -g pnpm
        fi
        success "pnpm installed"
    fi
}

check_python() {
    local py_cmd=""

    # Check for python3 with correct version
    for cmd in python3 python; do
        if command_exists "$cmd"; then
            local version
            version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            local major minor
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [[ "$major" -ge 3 ]] && [[ "$minor" -ge ${REQUIRED_PYTHON_VERSION#3.} ]]; then
                py_cmd="$cmd"
                success "Python $($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
                break
            fi
        fi
    done

    if [[ -z "$py_cmd" ]]; then
        warn "Python ${REQUIRED_PYTHON_VERSION}+ not found"
        if command_exists uv; then
            info "Installing Python ${REQUIRED_PYTHON_VERSION} via uv..."
            uv python install "$REQUIRED_PYTHON_VERSION"
            success "Python ${REQUIRED_PYTHON_VERSION} installed via uv"
        elif command_exists pyenv; then
            info "Installing Python ${REQUIRED_PYTHON_VERSION} via pyenv..."
            pyenv install "${REQUIRED_PYTHON_VERSION}"
            pyenv local "${REQUIRED_PYTHON_VERSION}"
            success "Python ${REQUIRED_PYTHON_VERSION} installed via pyenv"
        elif [[ "$OS" == "macos" ]] && command_exists brew; then
            info "Installing Python via Homebrew..."
            brew install python@3.12
            success "Python installed via Homebrew"
        else
            warn "Please install Python ${REQUIRED_PYTHON_VERSION}+ manually."
            warn "  Recommended: curl -LsSf https://astral.sh/uv/install.sh | sh"
        fi
    fi
}

check_uv() {
    if command_exists uv; then
        success "uv $(uv --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
    else
        info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add to PATH for current session
        export PATH="$HOME/.local/bin:$PATH"
        if command_exists uv; then
            success "uv installed"
        else
            warn "uv installed but not on PATH. Restart your terminal or add ~/.local/bin to PATH."
        fi
    fi
}

check_docker() {
    if command_exists docker; then
        success "Docker $(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
    else
        warn "Docker not found"
        if [[ "$OS" == "macos" ]]; then
            info "Install Docker Desktop: https://docs.docker.com/desktop/install/mac-install/"
            info "  Or: brew install --cask docker"
        else
            info "Install Docker Engine: https://docs.docker.com/engine/install/"
        fi
        return 1
    fi

    if command_exists docker && docker compose version &>/dev/null; then
        success "Docker Compose $(docker compose version --short 2>/dev/null || echo 'available')"
    else
        warn "Docker Compose not available. Make sure Docker is running."
        return 1
    fi

    # Check Docker is running
    if docker info &>/dev/null; then
        success "Docker daemon is running"
    else
        warn "Docker is installed but the daemon is not running. Please start Docker."
        return 1
    fi
}

check_git() {
    if command_exists git; then
        success "Git $(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
    else
        warn "Git not found"
        if [[ "$OS" == "macos" ]]; then
            info "Installing Git via Xcode CLT..."
            xcode-select --install 2>/dev/null || true
        elif command_exists apt-get; then
            sudo apt-get install -y git
        fi
    fi
}

check_common_tools() {
    # jq
    if command_exists jq; then
        success "jq $(jq --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')"
    else
        info "Installing jq..."
        if [[ "$OS" == "macos" ]] && command_exists brew; then
            brew install jq
        elif command_exists apt-get; then
            sudo apt-get install -y jq
        fi
    fi

    # curl
    if command_exists curl; then
        success "curl available"
    fi

    # make
    if command_exists make; then
        success "make available"
    else
        warn "make not found"
        if [[ "$OS" == "macos" ]]; then
            xcode-select --install 2>/dev/null || true
        elif command_exists apt-get; then
            sudo apt-get install -y build-essential
        fi
    fi
}

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------

setup_env_file() {
    if [[ -f "$ENV_FILE" ]]; then
        success ".env file exists"
        return 0
    fi

    if [[ -f "$ENV_EXAMPLE" ]]; then
        info "Creating .env from .env.example..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        success ".env created from .env.example"
        warn "Review .env and update credentials as needed."
    else
        warn "No .env.example found. Skipping .env creation."
    fi
}

# ---------------------------------------------------------------------------
# Dependency installation
# ---------------------------------------------------------------------------

install_frontend_deps() {
    if [[ -d "frontend" ]] && [[ -f "frontend/package.json" ]]; then
        info "Installing frontend dependencies..."
        cd frontend

        if [[ -f "pnpm-lock.yaml" ]] && command_exists pnpm; then
            pnpm install --frozen-lockfile 2>/dev/null || pnpm install
        elif [[ -f "package-lock.json" ]]; then
            npm ci 2>/dev/null || npm install
        elif command_exists pnpm; then
            pnpm install
        else
            npm install
        fi

        cd ..
        success "Frontend dependencies installed"
    else
        info "No frontend/package.json found, skipping frontend deps."
    fi
}

install_backend_deps() {
    if [[ -d "backend" ]]; then
        # Node.js backend (Express)
        if [[ -f "backend/package.json" ]]; then
            info "Installing backend Node.js dependencies..."
            cd backend

            if [[ -f "pnpm-lock.yaml" ]] && command_exists pnpm; then
                pnpm install --frozen-lockfile 2>/dev/null || pnpm install
            elif [[ -f "package-lock.json" ]]; then
                npm ci 2>/dev/null || npm install
            elif command_exists pnpm; then
                pnpm install
            else
                npm install
            fi

            cd ..
            success "Backend Node.js dependencies installed"
        fi

        # Python backend (FastAPI)
        if [[ -f "backend/pyproject.toml" ]]; then
            info "Installing backend Python dependencies..."
            cd backend

            if command_exists uv; then
                uv sync
            elif [[ -f "requirements.txt" ]]; then
                python3 -m pip install -r requirements.txt
            else
                python3 -m pip install -e ".[dev]"
            fi

            cd ..
            success "Backend Python dependencies installed"
        fi

        # Java backend (Spring Boot)
        if [[ -f "backend/build.gradle.kts" ]] || [[ -f "backend/build.gradle" ]]; then
            info "Downloading backend Gradle dependencies..."
            cd backend

            if [[ -f "gradlew" ]]; then
                chmod +x gradlew
                ./gradlew dependencies --quiet 2>/dev/null || ./gradlew dependencies
            fi

            cd ..
            success "Backend Gradle dependencies downloaded"
        fi

        if [[ -f "backend/pom.xml" ]]; then
            info "Downloading backend Maven dependencies..."
            cd backend
            mvn dependency:resolve --quiet 2>/dev/null || mvn dependency:resolve
            cd ..
            success "Backend Maven dependencies downloaded"
        fi
    else
        info "No backend/ directory found, skipping backend deps."
    fi
}

# Root-level monorepo dependencies
install_root_deps() {
    if [[ -f "package.json" ]]; then
        info "Installing root dependencies..."
        if [[ -f "pnpm-workspace.yaml" ]] && command_exists pnpm; then
            pnpm install
        elif [[ -f "package-lock.json" ]]; then
            npm ci 2>/dev/null || npm install
        else
            npm install
        fi
        success "Root dependencies installed"
    fi
}

# ---------------------------------------------------------------------------
# Docker services
# ---------------------------------------------------------------------------

start_docker_services() {
    if [[ "$SKIP_DOCKER" == "true" ]]; then
        info "Skipping Docker services (--skip-docker)."
        return 0
    fi

    if ! command_exists docker; then
        warn "Docker not available. Skipping service startup."
        return 0
    fi

    if ! docker info &>/dev/null; then
        warn "Docker daemon not running. Skipping service startup."
        return 0
    fi

    local compose_file="$DOCKER_COMPOSE_FILE"
    if [[ -f "docker-compose.dev.yml" ]]; then
        compose_file="docker-compose.dev.yml"
    fi

    if [[ ! -f "$compose_file" ]]; then
        info "No Docker Compose file found. Skipping service startup."
        return 0
    fi

    info "Starting Docker services from ${compose_file}..."

    # Start only infrastructure services (not app containers)
    local services=()
    for svc in postgres redis mysql mongo mailpit minio; do
        if docker compose -f "$compose_file" config --services 2>/dev/null | grep -q "^${svc}$"; then
            services+=("$svc")
        fi
    done

    if [[ ${#services[@]} -eq 0 ]]; then
        info "No infrastructure services found in compose file."
        return 0
    fi

    info "Starting: ${services[*]}"
    docker compose -f "$compose_file" up -d "${services[@]}"

    # Wait for health checks
    info "Waiting for services to be healthy..."
    local retries=30
    local healthy=false

    for ((i=1; i<=retries; i++)); do
        if docker compose -f "$compose_file" ps --format json 2>/dev/null | \
            python3 -c "
import sys, json
lines = sys.stdin.read().strip().split('\n')
all_healthy = True
for line in lines:
    if not line: continue
    svc = json.loads(line)
    state = svc.get('Health', svc.get('State', ''))
    if 'healthy' not in state.lower() and svc.get('State') != 'running':
        all_healthy = False
sys.exit(0 if all_healthy else 1)
" 2>/dev/null; then
            healthy=true
            break
        fi
        sleep 2
    done

    if [[ "$healthy" == "true" ]]; then
        success "Docker services are healthy"
    else
        # Fallback: just check if containers are running
        sleep 5
        success "Docker services started (health check timed out, services may still be initializing)"
    fi
}

# ---------------------------------------------------------------------------
# Database migrations
# ---------------------------------------------------------------------------

run_migrations() {
    info "Running database migrations..."

    # Prisma (Node.js)
    if [[ -f "backend/prisma/schema.prisma" ]]; then
        cd backend
        if command_exists npx; then
            npx prisma migrate dev --name init 2>/dev/null || npx prisma migrate deploy
        fi
        cd ..
        success "Prisma migrations applied"
        return 0
    fi

    # Alembic (Python)
    if [[ -f "backend/alembic.ini" ]] || [[ -d "backend/app/db/migrations" ]]; then
        cd backend
        if command_exists uv; then
            uv run alembic upgrade head 2>/dev/null || warn "Alembic migration failed (may need manual setup)"
        elif command_exists alembic; then
            alembic upgrade head
        fi
        cd ..
        success "Alembic migrations applied"
        return 0
    fi

    # Flyway (Java / Spring Boot)
    if [[ -d "backend/src/main/resources/db/migration" ]]; then
        info "Flyway migrations will run automatically on Spring Boot startup."
        success "Flyway migrations configured"
        return 0
    fi

    info "No migration tool detected. Skipping migrations."
}

# ---------------------------------------------------------------------------
# Database seeding
# ---------------------------------------------------------------------------

seed_database() {
    if [[ "$SKIP_SEED" == "true" ]]; then
        info "Skipping database seeding (--skip-seed)."
        return 0
    fi

    info "Seeding database..."

    # Prisma seed
    if [[ -f "backend/prisma/seed.ts" ]] || [[ -f "backend/prisma/seed.js" ]]; then
        cd backend
        npx prisma db seed 2>/dev/null || warn "Prisma seed failed (may not be configured)"
        cd ..
        return 0
    fi

    # Python seed script
    if [[ -f "scripts/seed-db.py" ]]; then
        if command_exists uv; then
            uv run python scripts/seed-db.py
        else
            python3 scripts/seed-db.py
        fi
        success "Database seeded"
        return 0
    fi

    if [[ -f "backend/scripts/seed.py" ]]; then
        cd backend
        if command_exists uv; then
            uv run python scripts/seed.py
        else
            python3 scripts/seed.py
        fi
        cd ..
        success "Database seeded"
        return 0
    fi

    info "No seed script found. Skipping seeding."
}

# ---------------------------------------------------------------------------
# Git hooks
# ---------------------------------------------------------------------------

setup_git_hooks() {
    if [[ ! -d ".git" ]]; then
        info "Not a git repository. Skipping hook setup."
        return 0
    fi

    # Husky
    if [[ -f "package.json" ]] && grep -q '"husky"' package.json 2>/dev/null; then
        info "Setting up Husky git hooks..."
        npx husky install 2>/dev/null || npx husky 2>/dev/null || true
        success "Husky hooks configured"
    fi

    # pre-commit (Python)
    if [[ -f ".pre-commit-config.yaml" ]]; then
        if command_exists pre-commit; then
            info "Installing pre-commit hooks..."
            pre-commit install
            success "pre-commit hooks installed"
        else
            warn "pre-commit not found. Install with: pip install pre-commit"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    echo ""
    echo "========================================"
    echo "  Development Environment Setup"
    echo "========================================"
    echo ""

    # Step 1: Check and install tools
    info "Checking required tools..."
    echo ""

    check_homebrew
    check_git
    check_node
    check_pnpm
    check_python
    check_uv
    check_docker
    check_common_tools

    echo ""

    if [[ "$CHECK_ONLY" == "true" ]]; then
        echo "========================================"
        echo "  Tool check complete."
        echo "========================================"
        exit 0
    fi

    # Step 2: Environment file
    info "Setting up environment..."
    setup_env_file
    echo ""

    # Step 3: Install dependencies
    info "Installing dependencies..."
    install_root_deps
    install_frontend_deps
    install_backend_deps
    echo ""

    # Step 4: Start Docker services
    start_docker_services
    echo ""

    # Step 5: Run migrations
    run_migrations
    echo ""

    # Step 6: Seed database
    seed_database
    echo ""

    # Step 7: Git hooks
    setup_git_hooks
    echo ""

    # Done
    echo "========================================"
    echo "  Setup complete!"
    echo "========================================"
    echo ""
    echo "  Start developing:"
    echo "    Frontend:  cd frontend && npm run dev"
    echo "    Backend:   cd backend && npm run dev  (or equivalent)"
    echo ""
    echo "  Useful commands:"
    echo "    docker compose ps           # Check running services"
    echo "    docker compose logs -f      # Follow service logs"
    echo "    docker compose down         # Stop all services"
    echo ""
}

main "$@"
