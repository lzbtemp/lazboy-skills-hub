#!/usr/bin/env python3
"""
generate_dockerfile.py — Dockerfile Generator

Detects the project type and generates a production-ready multi-stage Dockerfile
with proper base images, dependency caching, non-root user, and health checks.

Supported project types:
  - Node.js   (package.json)
  - Python    (pyproject.toml, requirements.txt, Pipfile)
  - Java      (pom.xml, build.gradle, build.gradle.kts)

Usage:
    python generate_dockerfile.py                      # Detect from current directory
    python generate_dockerfile.py /path/to/project     # Detect from specified directory
    python generate_dockerfile.py --type node          # Force project type
    python generate_dockerfile.py --output Dockerfile  # Custom output path
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ProjectType(Enum):
    NODEJS = "node"
    PYTHON = "python"
    JAVA_MAVEN = "java-maven"
    JAVA_GRADLE = "java-gradle"
    UNKNOWN = "unknown"


@dataclass
class ProjectInfo:
    """Detected project metadata."""

    project_type: ProjectType
    name: str = "app"
    version: str = "1.0.0"
    entry_point: str = ""
    port: int = 3000
    node_version: str = "20"
    python_version: str = "3.12"
    java_version: str = "21"
    has_typescript: bool = False
    has_prisma: bool = False
    has_next: bool = False
    package_manager: str = "npm"  # npm, yarn, pnpm
    python_framework: str = ""  # fastapi, flask, django
    build_command: str = ""
    start_command: str = ""


# ---------------------------------------------------------------------------
# Project Detection
# ---------------------------------------------------------------------------


def detect_project(project_dir: Path) -> ProjectInfo:
    """Auto-detect the project type and gather metadata from config files."""

    # Check Node.js
    package_json = project_dir / "package.json"
    if package_json.exists():
        return _detect_nodejs(project_dir, package_json)

    # Check Python
    pyproject = project_dir / "pyproject.toml"
    requirements = project_dir / "requirements.txt"
    pipfile = project_dir / "Pipfile"
    if pyproject.exists() or requirements.exists() or pipfile.exists():
        return _detect_python(project_dir)

    # Check Java - Maven
    pom_xml = project_dir / "pom.xml"
    if pom_xml.exists():
        return _detect_java_maven(project_dir, pom_xml)

    # Check Java - Gradle
    build_gradle = project_dir / "build.gradle"
    build_gradle_kts = project_dir / "build.gradle.kts"
    if build_gradle.exists() or build_gradle_kts.exists():
        return _detect_java_gradle(project_dir)

    return ProjectInfo(project_type=ProjectType.UNKNOWN)


def _detect_nodejs(project_dir: Path, package_json: Path) -> ProjectInfo:
    """Detect Node.js project details from package.json."""
    try:
        pkg = json.loads(package_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pkg = {}

    info = ProjectInfo(project_type=ProjectType.NODEJS)
    info.name = pkg.get("name", "app")
    info.version = pkg.get("version", "1.0.0")
    info.port = 3000

    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

    # Detect package manager
    if (project_dir / "pnpm-lock.yaml").exists():
        info.package_manager = "pnpm"
    elif (project_dir / "yarn.lock").exists():
        info.package_manager = "yarn"
    else:
        info.package_manager = "npm"

    # Detect TypeScript
    info.has_typescript = "typescript" in deps or (project_dir / "tsconfig.json").exists()

    # Detect frameworks
    info.has_next = "next" in deps
    info.has_prisma = "@prisma/client" in deps

    # Determine build and start commands
    scripts = pkg.get("scripts", {})
    info.build_command = "build" if "build" in scripts else ""
    info.start_command = scripts.get("start", "node dist/index.js" if info.has_typescript else "node index.js")

    if info.has_next:
        info.port = 3000
        info.start_command = "next start"
        info.build_command = "build"

    # Determine entry point
    info.entry_point = pkg.get("main", "dist/index.js" if info.has_typescript else "index.js")

    return info


def _detect_python(project_dir: Path) -> ProjectInfo:
    """Detect Python project details."""
    info = ProjectInfo(project_type=ProjectType.PYTHON)
    info.port = 8000

    # Check for framework in requirements
    all_deps = ""
    req_file = project_dir / "requirements.txt"
    if req_file.exists():
        all_deps = req_file.read_text(encoding="utf-8").lower()

    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        all_deps += pyproject.read_text(encoding="utf-8").lower()

    if "fastapi" in all_deps or "uvicorn" in all_deps:
        info.python_framework = "fastapi"
        info.start_command = "uvicorn app.main:app --host 0.0.0.0 --port 8000"
    elif "flask" in all_deps:
        info.python_framework = "flask"
        info.start_command = "gunicorn --bind 0.0.0.0:8000 --workers 4 app:app"
        info.port = 8000
    elif "django" in all_deps:
        info.python_framework = "django"
        info.start_command = "gunicorn --bind 0.0.0.0:8000 --workers 4 config.wsgi:application"
        info.port = 8000
    else:
        info.start_command = "python -m app"

    # Detect name from pyproject.toml
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8")
        name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
        if name_match:
            info.name = name_match.group(1)

    return info


def _detect_java_maven(project_dir: Path, pom_xml: Path) -> ProjectInfo:
    """Detect Java Maven project details."""
    info = ProjectInfo(project_type=ProjectType.JAVA_MAVEN)
    info.port = 8080

    content = pom_xml.read_text(encoding="utf-8")

    # Extract artifact name
    match = re.search(r"<artifactId>([^<]+)</artifactId>", content)
    if match:
        info.name = match.group(1)

    version_match = re.search(r"<version>([^<]+)</version>", content)
    if version_match:
        info.version = version_match.group(1)

    info.build_command = "./mvnw package -DskipTests"
    info.start_command = f"java -jar target/{info.name}-{info.version}.jar"
    info.entry_point = f"target/{info.name}-{info.version}.jar"

    return info


def _detect_java_gradle(project_dir: Path) -> ProjectInfo:
    """Detect Java Gradle project details."""
    info = ProjectInfo(project_type=ProjectType.JAVA_GRADLE)
    info.port = 8080
    info.name = project_dir.name
    info.build_command = "./gradlew bootJar"
    info.start_command = f"java -jar build/libs/{info.name}.jar"
    info.entry_point = f"build/libs/{info.name}.jar"

    return info


# ---------------------------------------------------------------------------
# Dockerfile Generators
# ---------------------------------------------------------------------------


def generate_nodejs_dockerfile(info: ProjectInfo) -> str:
    """Generate a multi-stage Dockerfile for a Node.js project."""

    # Package manager commands
    if info.package_manager == "pnpm":
        install_cmd = "RUN corepack enable pnpm"
        copy_lockfile = "COPY pnpm-lock.yaml ./"
        install_deps = "RUN pnpm install --frozen-lockfile"
        install_prod = "RUN pnpm install --frozen-lockfile --prod"
        build_cmd = "RUN pnpm run build" if info.build_command else ""
    elif info.package_manager == "yarn":
        install_cmd = ""
        copy_lockfile = "COPY yarn.lock ./"
        install_deps = "RUN yarn install --frozen-lockfile"
        install_prod = "RUN yarn install --frozen-lockfile --production"
        build_cmd = "RUN yarn build" if info.build_command else ""
    else:
        install_cmd = ""
        copy_lockfile = "COPY package-lock.json ./"
        install_deps = "RUN npm ci"
        install_prod = "RUN npm ci --only=production"
        build_cmd = "RUN npm run build" if info.build_command else ""

    prisma_step = ""
    prisma_copy = ""
    if info.has_prisma:
        prisma_step = "\n# Generate Prisma client\nCOPY prisma ./prisma/\nRUN npx prisma generate"
        prisma_copy = "\nCOPY --from=builder --chown=appuser:appgroup /app/prisma ./prisma"

    lines = [
        "# syntax=docker/dockerfile:1",
        "",
        "# ============================================",
        "# Stage 1: Dependencies",
        "# ============================================",
        f"FROM node:{info.node_version}-alpine AS deps",
        "",
        "WORKDIR /app",
        "",
        "RUN apk add --no-cache libc6-compat",
    ]

    if install_cmd:
        lines.append(install_cmd)

    lines += [
        "",
        "COPY package.json ./",
        copy_lockfile,
        install_deps,
        "",
        "# ============================================",
        "# Stage 2: Build",
        "# ============================================",
        f"FROM node:{info.node_version}-alpine AS builder",
        "",
        "WORKDIR /app",
        "",
        "COPY --from=deps /app/node_modules ./node_modules",
        "COPY . .",
    ]

    if prisma_step:
        lines.append(prisma_step)

    if build_cmd:
        lines += ["", build_cmd]

    lines += [
        "",
        "# ============================================",
        "# Stage 3: Production",
        "# ============================================",
        f"FROM node:{info.node_version}-alpine AS runner",
        "",
        "RUN addgroup --system --gid 1001 appgroup && \\",
        "    adduser --system --uid 1001 appuser",
        "",
        "RUN apk add --no-cache tini",
        "",
        "WORKDIR /app",
        "",
        "COPY --from=builder --chown=appuser:appgroup /app/package.json ./",
    ]

    if info.has_next:
        lines += [
            "COPY --from=builder --chown=appuser:appgroup /app/.next/standalone ./",
            "COPY --from=builder --chown=appuser:appgroup /app/.next/static ./.next/static",
            "COPY --from=builder --chown=appuser:appgroup /app/public ./public",
        ]
    elif build_cmd:
        lines += [
            "COPY --from=builder --chown=appuser:appgroup /app/dist ./dist",
            "COPY --from=deps --chown=appuser:appgroup /app/node_modules ./node_modules",
        ]
    else:
        lines += [
            "COPY --from=builder --chown=appuser:appgroup /app ./ ",
            "COPY --from=deps --chown=appuser:appgroup /app/node_modules ./node_modules",
        ]

    if prisma_copy:
        lines.append(prisma_copy)

    lines += [
        "",
        "USER appuser",
        "",
        "ENV NODE_ENV=production",
        f"ENV PORT={info.port}",
        "",
        f"EXPOSE {info.port}",
        "",
        "HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\",
        f'  CMD wget --no-verbose --tries=1 --spider http://localhost:{info.port}/health || exit 1',
        "",
        'ENTRYPOINT ["tini", "--"]',
    ]

    if info.has_next:
        lines.append('CMD ["node", "server.js"]')
    else:
        start_parts = info.start_command.split()
        cmd_json = json.dumps(start_parts)
        lines.append(f"CMD {cmd_json}")

    lines.append("")
    return "\n".join(lines)


def generate_python_dockerfile(info: ProjectInfo) -> str:
    """Generate a multi-stage Dockerfile for a Python project."""

    lines = [
        "# syntax=docker/dockerfile:1",
        "",
        "# ============================================",
        "# Stage 1: Build",
        "# ============================================",
        f"FROM python:{info.python_version}-slim AS builder",
        "",
        "WORKDIR /app",
        "",
        "RUN apt-get update && \\",
        "    apt-get install -y --no-install-recommends gcc libpq-dev && \\",
        "    rm -rf /var/lib/apt/lists/*",
        "",
        "RUN python -m venv /opt/venv",
        'ENV PATH="/opt/venv/bin:$PATH"',
        "",
        "COPY requirements*.txt ./",
        "RUN pip install --no-cache-dir --upgrade pip && \\",
        "    pip install --no-cache-dir -r requirements.txt",
        "",
        "COPY . .",
    ]

    # If pyproject.toml exists, install the package
    lines += [
        "",
        "# Install app package if pyproject.toml exists",
        "RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir .; fi",
    ]

    lines += [
        "",
        "# ============================================",
        "# Stage 2: Production",
        "# ============================================",
        f"FROM python:{info.python_version}-slim AS runner",
        "",
        "RUN apt-get update && \\",
        "    apt-get install -y --no-install-recommends libpq5 curl tini && \\",
        "    rm -rf /var/lib/apt/lists/*",
        "",
        "RUN groupadd --gid 1001 appgroup && \\",
        "    useradd --uid 1001 --gid appgroup --shell /bin/sh --create-home appuser",
        "",
        "WORKDIR /app",
        "",
        "COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv",
        "COPY --from=builder --chown=appuser:appgroup /app .",
        "",
        'ENV PATH="/opt/venv/bin:$PATH"',
        "ENV PYTHONUNBUFFERED=1",
        "ENV PYTHONDONTWRITEBYTECODE=1",
        f"ENV PORT={info.port}",
        "",
        "USER appuser",
        "",
        f"EXPOSE {info.port}",
        "",
        "HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \\",
        f"  CMD curl -f http://localhost:{info.port}/health || exit 1",
        "",
        'ENTRYPOINT ["tini", "--"]',
    ]

    start_parts = info.start_command.split()
    cmd_json = json.dumps(start_parts)
    lines.append(f"CMD {cmd_json}")
    lines.append("")
    return "\n".join(lines)


def generate_java_maven_dockerfile(info: ProjectInfo) -> str:
    """Generate a multi-stage Dockerfile for a Java Maven project."""

    lines = [
        "# syntax=docker/dockerfile:1",
        "",
        "# ============================================",
        "# Stage 1: Build",
        "# ============================================",
        f"FROM eclipse-temurin:{info.java_version}-jdk-jammy AS builder",
        "",
        "WORKDIR /app",
        "",
        "# Copy Maven wrapper and POM first for dependency caching",
        "COPY mvnw ./",
        "COPY .mvn .mvn",
        "COPY pom.xml ./",
        "",
        "# Make wrapper executable and download dependencies",
        "RUN chmod +x mvnw && \\",
        "    ./mvnw dependency:go-offline -B",
        "",
        "# Copy source and build",
        "COPY src ./src",
        "RUN ./mvnw package -DskipTests -B",
        "",
        "# ============================================",
        "# Stage 2: Production",
        "# ============================================",
        f"FROM eclipse-temurin:{info.java_version}-jre-jammy AS runner",
        "",
        "RUN apt-get update && \\",
        "    apt-get install -y --no-install-recommends curl tini && \\",
        "    rm -rf /var/lib/apt/lists/*",
        "",
        "RUN groupadd --gid 1001 appgroup && \\",
        "    useradd --uid 1001 --gid appgroup --shell /bin/sh --create-home appuser",
        "",
        "WORKDIR /app",
        "",
        f"COPY --from=builder --chown=appuser:appgroup /app/{info.entry_point} app.jar",
        "",
        "USER appuser",
        "",
        f"ENV PORT={info.port}",
        "ENV JAVA_OPTS=\"-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0 -XX:+ExitOnOutOfMemoryError\"",
        "",
        f"EXPOSE {info.port}",
        "",
        "HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \\",
        f"  CMD curl -f http://localhost:{info.port}/actuator/health || exit 1",
        "",
        'ENTRYPOINT ["tini", "--"]',
        'CMD ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]',
        "",
    ]
    return "\n".join(lines)


def generate_java_gradle_dockerfile(info: ProjectInfo) -> str:
    """Generate a multi-stage Dockerfile for a Java Gradle project."""

    lines = [
        "# syntax=docker/dockerfile:1",
        "",
        "# ============================================",
        "# Stage 1: Build",
        "# ============================================",
        f"FROM eclipse-temurin:{info.java_version}-jdk-jammy AS builder",
        "",
        "WORKDIR /app",
        "",
        "# Copy Gradle wrapper and build files first for dependency caching",
        "COPY gradlew ./",
        "COPY gradle gradle",
        "COPY build.gradle* ./",
        "COPY settings.gradle* ./",
        "",
        "RUN chmod +x gradlew && \\",
        "    ./gradlew dependencies --no-daemon",
        "",
        "# Copy source and build",
        "COPY src ./src",
        "RUN ./gradlew bootJar --no-daemon",
        "",
        "# ============================================",
        "# Stage 2: Production",
        "# ============================================",
        f"FROM eclipse-temurin:{info.java_version}-jre-jammy AS runner",
        "",
        "RUN apt-get update && \\",
        "    apt-get install -y --no-install-recommends curl tini && \\",
        "    rm -rf /var/lib/apt/lists/*",
        "",
        "RUN groupadd --gid 1001 appgroup && \\",
        "    useradd --uid 1001 --gid appgroup --shell /bin/sh --create-home appuser",
        "",
        "WORKDIR /app",
        "",
        f"COPY --from=builder --chown=appuser:appgroup /app/{info.entry_point} app.jar",
        "",
        "USER appuser",
        "",
        f"ENV PORT={info.port}",
        "ENV JAVA_OPTS=\"-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0 -XX:+ExitOnOutOfMemoryError\"",
        "",
        f"EXPOSE {info.port}",
        "",
        "HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \\",
        f"  CMD curl -f http://localhost:{info.port}/actuator/health || exit 1",
        "",
        'ENTRYPOINT ["tini", "--"]',
        'CMD ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]',
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# .dockerignore Generator
# ---------------------------------------------------------------------------


def generate_dockerignore(info: ProjectInfo) -> str:
    """Generate a .dockerignore file appropriate for the project type."""

    common = [
        "# Version control",
        ".git",
        ".gitignore",
        "",
        "# IDE",
        ".vscode",
        ".idea",
        "*.swp",
        "*.swo",
        "",
        "# Environment and secrets",
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        "",
        "# Docker",
        "Dockerfile*",
        "docker-compose*",
        ".dockerignore",
        "",
        "# Documentation",
        "*.md",
        "LICENSE",
        "docs/",
    ]

    if info.project_type == ProjectType.NODEJS:
        common += [
            "",
            "# Node.js",
            "node_modules",
            ".next",
            "dist",
            "build",
            "coverage",
            ".nyc_output",
            "*.log",
        ]
    elif info.project_type == ProjectType.PYTHON:
        common += [
            "",
            "# Python",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".venv",
            "venv",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "htmlcov",
            "*.egg-info",
        ]
    elif info.project_type in (ProjectType.JAVA_MAVEN, ProjectType.JAVA_GRADLE):
        common += [
            "",
            "# Java",
            "target/",
            "build/",
            ".gradle/",
            "*.class",
            "*.jar",
            "*.war",
        ]

    return "\n".join(common) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

GENERATORS = {
    ProjectType.NODEJS: generate_nodejs_dockerfile,
    ProjectType.PYTHON: generate_python_dockerfile,
    ProjectType.JAVA_MAVEN: generate_java_maven_dockerfile,
    ProjectType.JAVA_GRADLE: generate_java_gradle_dockerfile,
}

TYPE_MAP = {
    "node": ProjectType.NODEJS,
    "nodejs": ProjectType.NODEJS,
    "python": ProjectType.PYTHON,
    "java-maven": ProjectType.JAVA_MAVEN,
    "maven": ProjectType.JAVA_MAVEN,
    "java-gradle": ProjectType.JAVA_GRADLE,
    "gradle": ProjectType.JAVA_GRADLE,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a production-ready Dockerfile for your project."
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        type=Path,
        default=Path("."),
        help="Project directory (default: current directory).",
    )
    parser.add_argument(
        "--type",
        "-t",
        type=str,
        default=None,
        choices=list(TYPE_MAP.keys()),
        help="Force a specific project type instead of auto-detecting.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="Dockerfile",
        help="Output filename (default: Dockerfile).",
    )
    parser.add_argument(
        "--dockerignore",
        action="store_true",
        help="Also generate a .dockerignore file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print to stdout instead of writing files.",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a directory.", file=sys.stderr)
        sys.exit(1)

    # Detect or force project type
    if args.type:
        forced_type = TYPE_MAP[args.type]
        info = detect_project(project_dir)
        info.project_type = forced_type
        print(f"Forced project type: {forced_type.value}")
    else:
        info = detect_project(project_dir)
        print(f"Detected project type: {info.project_type.value}")

    if info.project_type == ProjectType.UNKNOWN:
        print(
            "Error: Could not detect project type. "
            "Use --type to specify manually.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"  Name: {info.name}")
    print(f"  Port: {info.port}")
    if info.start_command:
        print(f"  Start: {info.start_command}")

    # Generate Dockerfile
    generator = GENERATORS[info.project_type]
    dockerfile_content = generator(info)

    if args.dry_run:
        print("\n--- Dockerfile ---")
        print(dockerfile_content)
    else:
        output_path = project_dir / args.output
        output_path.write_text(dockerfile_content, encoding="utf-8")
        print(f"\nWritten: {output_path}")

    # Generate .dockerignore
    if args.dockerignore:
        ignore_content = generate_dockerignore(info)
        if args.dry_run:
            print("\n--- .dockerignore ---")
            print(ignore_content)
        else:
            ignore_path = project_dir / ".dockerignore"
            ignore_path.write_text(ignore_content, encoding="utf-8")
            print(f"Written: {ignore_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
