#!/usr/bin/env python3
"""Generate a GitHub Actions CI/CD workflow based on detected project type.

Scans a project directory for configuration files (package.json, pyproject.toml,
Dockerfile, etc.) and generates an appropriate GitHub Actions workflow YAML.

Usage:
    python setup_pipeline.py --project-dir /path/to/project
    python setup_pipeline.py --project-dir . --output .github/workflows/ci.yml
    python setup_pipeline.py --project-dir . --type python --name "My CI"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import NamedTuple


class ProjectInfo(NamedTuple):
    project_type: str  # node, python, docker, terraform, unknown
    has_dockerfile: bool
    has_tests: bool
    package_manager: str  # npm, yarn, pnpm, pip, poetry, uv
    framework: str  # react, next, express, fastapi, flask, django, none


def detect_project(project_dir: Path) -> ProjectInfo:
    """Detect project type by scanning for known configuration files."""
    has_dockerfile = (project_dir / "Dockerfile").exists()

    # Node.js detection
    if (project_dir / "package.json").exists():
        try:
            with open(project_dir / "package.json") as f:
                pkg = json.load(f)
        except (json.JSONDecodeError, OSError):
            pkg = {}

        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        # Package manager
        if (project_dir / "pnpm-lock.yaml").exists():
            pm = "pnpm"
        elif (project_dir / "yarn.lock").exists():
            pm = "yarn"
        else:
            pm = "npm"

        # Framework
        framework = "none"
        if "next" in deps:
            framework = "next"
        elif "react-scripts" in deps or "react" in deps:
            framework = "react"
        elif "express" in deps:
            framework = "express"

        has_tests = "test" in pkg.get("scripts", {}) or (project_dir / "jest.config.js").exists()

        return ProjectInfo(
            project_type="node",
            has_dockerfile=has_dockerfile,
            has_tests=has_tests,
            package_manager=pm,
            framework=framework,
        )

    # Python detection
    if (project_dir / "pyproject.toml").exists() or (project_dir / "requirements.txt").exists():
        # Package manager
        if (project_dir / "uv.lock").exists():
            pm = "uv"
        elif (project_dir / "poetry.lock").exists():
            pm = "poetry"
        else:
            pm = "pip"

        # Framework detection
        framework = "none"
        req_files = ["requirements.txt", "pyproject.toml", "setup.cfg"]
        for req_file in req_files:
            req_path = project_dir / req_file
            if req_path.exists():
                try:
                    content = req_path.read_text().lower()
                    if "fastapi" in content:
                        framework = "fastapi"
                        break
                    elif "flask" in content:
                        framework = "flask"
                        break
                    elif "django" in content:
                        framework = "django"
                        break
                except OSError:
                    continue

        has_tests = (
            (project_dir / "tests").is_dir()
            or (project_dir / "test").is_dir()
            or any(project_dir.glob("test_*.py"))
            or any(project_dir.glob("*_test.py"))
        )

        return ProjectInfo(
            project_type="python",
            has_dockerfile=has_dockerfile,
            has_tests=has_tests,
            package_manager=pm,
            framework=framework,
        )

    # Terraform detection
    if any(project_dir.glob("*.tf")):
        return ProjectInfo(
            project_type="terraform",
            has_dockerfile=False,
            has_tests=(project_dir / "tests").is_dir(),
            package_manager="terraform",
            framework="none",
        )

    # Docker-only detection
    if has_dockerfile:
        return ProjectInfo(
            project_type="docker",
            has_dockerfile=True,
            has_tests=False,
            package_manager="docker",
            framework="none",
        )

    return ProjectInfo(
        project_type="unknown",
        has_dockerfile=has_dockerfile,
        has_tests=False,
        package_manager="unknown",
        framework="none",
    )


def generate_node_workflow(info: ProjectInfo, name: str) -> str:
    """Generate GitHub Actions workflow for a Node.js project."""
    install_cmd = {
        "npm": "npm ci",
        "yarn": "yarn install --frozen-lockfile",
        "pnpm": "pnpm install --frozen-lockfile",
    }.get(info.package_manager, "npm ci")

    cache_type = info.package_manager if info.package_manager in ("npm", "yarn", "pnpm") else "npm"

    run_prefix = {
        "npm": "npm run",
        "yarn": "yarn",
        "pnpm": "pnpm",
    }.get(info.package_manager, "npm run")

    test_step = ""
    if info.has_tests:
        test_step = f"""
  test:
    name: Test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "{cache_type}"

      - run: {install_cmd}

      - run: {run_prefix} test -- --coverage --ci
        env:
          CI: true

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage
          path: coverage/
          retention-days: 7
"""

    build_needs = "test" if info.has_tests else "lint"

    docker_job = ""
    if info.has_dockerfile:
        docker_job = f"""
  docker:
    name: Docker Build
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: {build_needs}
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    permissions:
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{{{ github.actor }}}}
          password: ${{{{ secrets.GITHUB_TOKEN }}}}

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{{{ github.repository }}}}:${{{{ github.sha }}}}
          cache-from: type=gha
          cache-to: type=gha,mode=max
"""

    return f"""name: {name}

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ${{{{ github.workflow }}}}-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "{cache_type}"

      - run: {install_cmd}

      - run: {run_prefix} lint --if-present
{test_step}
  build:
    name: Build
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: {build_needs}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "{cache_type}"

      - run: {install_cmd}

      - run: {run_prefix} build
{docker_job}"""


def generate_python_workflow(info: ProjectInfo, name: str) -> str:
    """Generate GitHub Actions workflow for a Python project."""
    if info.package_manager == "poetry":
        install_steps = """      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install"""
        test_cmd = "poetry run pytest"
        lint_prefix = "poetry run"
    elif info.package_manager == "uv":
        install_steps = """      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync"""
        test_cmd = "uv run pytest"
        lint_prefix = "uv run"
    else:
        install_steps = """      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install ruff pytest"""
        test_cmd = "pytest"
        lint_prefix = ""

    ruff_check = f"{lint_prefix} ruff check ." if lint_prefix else "ruff check ."
    ruff_format = f"{lint_prefix} ruff format --check ." if lint_prefix else "ruff format --check ."

    test_job = ""
    if info.has_tests:
        test_job = f"""
  test:
    name: Test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

{install_steps}

      - name: Run tests
        run: |
          {test_cmd} tests/ \\
            --cov=src \\
            --cov-report=xml \\
            --cov-report=term-missing \\
            -v
"""

    docker_job = ""
    if info.has_dockerfile:
        docker_needs = "test" if info.has_tests else "lint"
        docker_job = f"""
  docker:
    name: Docker Build
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: {docker_needs}
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    permissions:
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{{{ github.actor }}}}
          password: ${{{{ secrets.GITHUB_TOKEN }}}}

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{{{ github.repository }}}}:${{{{ github.sha }}}}
          cache-from: type=gha
          cache-to: type=gha,mode=max
"""

    return f"""name: {name}

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ${{{{ github.workflow }}}}-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

{install_steps}

      - name: Ruff check
        run: {ruff_check}

      - name: Ruff format
        run: {ruff_format}
{test_job}{docker_job}"""


def generate_docker_workflow(info: ProjectInfo, name: str) -> str:
    """Generate GitHub Actions workflow for a Docker-only project."""
    return f"""name: {name}

on:
  push:
    branches: [main]
    paths:
      - "Dockerfile"
      - "src/**"
  pull_request:
    branches: [main]

permissions:
  contents: read
  packages: write

concurrency:
  group: ${{{{ github.workflow }}}}-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
  build:
    name: Build & Push
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        if: github.event_name == 'push'
        with:
          registry: ghcr.io
          username: ${{{{ github.actor }}}}
          password: ${{{{ secrets.GITHUB_TOKEN }}}}

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{{{ github.event_name == 'push' }}}}
          tags: |
            ghcr.io/${{{{ github.repository }}}}:${{{{ github.sha }}}}
            ghcr.io/${{{{ github.repository }}}}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Trivy vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{{{ github.repository }}}}:${{{{ github.sha }}}}
          format: "table"
          severity: "CRITICAL,HIGH"
"""


def generate_terraform_workflow(info: ProjectInfo, name: str) -> str:
    """Generate GitHub Actions workflow for Terraform."""
    return f"""name: {name}

on:
  push:
    branches: [main]
    paths: ["infra/**"]
  pull_request:
    branches: [main]
    paths: ["infra/**"]

permissions:
  contents: read
  pull-requests: write
  id-token: write

env:
  TF_VERSION: "1.7"
  WORKING_DIR: infra

jobs:
  validate:
    name: Validate
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: ${{{{ env.WORKING_DIR }}}}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{{{ env.TF_VERSION }}}}

      - run: terraform fmt -check -recursive

      - run: terraform init -backend=false

      - run: terraform validate

  plan:
    name: Plan
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: validate
    defaults:
      run:
        working-directory: ${{{{ env.WORKING_DIR }}}}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{{{ env.TF_VERSION }}}}

      - run: terraform init

      - name: Terraform plan
        id: plan
        run: terraform plan -no-color -out=tfplan

  apply:
    name: Apply
    runs-on: ubuntu-latest
    timeout-minutes: 30
    needs: plan
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production
    defaults:
      run:
        working-directory: ${{{{ env.WORKING_DIR }}}}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{{{ env.TF_VERSION }}}}

      - run: terraform init

      - run: terraform apply -auto-approve
"""


GENERATORS = {
    "node": generate_node_workflow,
    "python": generate_python_workflow,
    "docker": generate_docker_workflow,
    "terraform": generate_terraform_workflow,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a GitHub Actions CI/CD workflow based on project type.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --project-dir .
  %(prog)s --project-dir /app --output .github/workflows/ci.yml
  %(prog)s --project-dir . --type python --name "Python CI"
        """,
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Path to the project directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output file path (default: .github/workflows/ci.yml relative to project-dir)",
    )
    parser.add_argument(
        "--type",
        choices=["node", "python", "docker", "terraform"],
        default=None,
        help="Override detected project type",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Workflow name (default: auto-generated based on project type)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the workflow to stdout without writing a file",
    )

    args = parser.parse_args()
    project_dir = args.project_dir.resolve()

    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a directory", file=sys.stderr)
        return 1

    # Detect project type
    info = detect_project(project_dir)
    project_type = args.type or info.project_type

    if project_type == "unknown":
        print(
            "Error: Could not detect project type. Use --type to specify.",
            file=sys.stderr,
        )
        print(f"  Scanned: {project_dir}", file=sys.stderr)
        return 1

    # If type was overridden, update info
    if args.type and args.type != info.project_type:
        info = info._replace(project_type=args.type)

    generator = GENERATORS.get(project_type)
    if not generator:
        print(f"Error: No generator for project type '{project_type}'", file=sys.stderr)
        return 1

    default_names = {
        "node": "Node.js CI",
        "python": "Python CI",
        "docker": "Docker Build",
        "terraform": "Terraform",
    }
    workflow_name = args.name or default_names.get(project_type, "CI")

    # Generate workflow
    workflow = generator(info, workflow_name)

    print(f"Detected project type: {project_type}")
    print(f"  Package manager: {info.package_manager}")
    print(f"  Framework: {info.framework}")
    print(f"  Has tests: {info.has_tests}")
    print(f"  Has Dockerfile: {info.has_dockerfile}")

    if args.dry_run:
        print("\n--- Generated Workflow ---\n")
        print(workflow)
        return 0

    # Write workflow file
    output_path = args.output or project_dir / ".github" / "workflows" / "ci.yml"
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(workflow)
    print(f"\nWorkflow written to: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
