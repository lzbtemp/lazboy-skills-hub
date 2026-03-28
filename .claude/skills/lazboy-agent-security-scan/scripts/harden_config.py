#!/usr/bin/env python3
"""Apply safe hardening fixes to Claude Code / AI agent configurations.

Only applies safe, non-breaking changes:
- Replace hardcoded secrets with environment variable references
- Add missing deny lists for destructive commands
- Add missing descriptions to MCP servers
- Remove dangerous permission wildcards (with confirmation)

Usage:
    python harden_config.py .
    python harden_config.py /path/to/project --dry-run
    python harden_config.py . --auto  # Apply without confirmation
"""

import argparse
import json
import re
import sys
from pathlib import Path


# Default deny list for destructive commands
DEFAULT_DENY_LIST = [
    "Bash(curl *)",
    "Bash(wget *)",
    "Bash(nc *)",
    "Bash(rm -rf *)",
    "Bash(chmod 777 *)",
    "Bash(sudo *)",
    "Bash(ssh *)",
    "Bash(scp *)",
    "Bash(git push --force *)",
    "Bash(git reset --hard *)",
    "Bash(git clean -fd *)",
]

# Dangerous allow list entries to flag/remove
DANGEROUS_ALLOWS = {
    "Bash(*)",
    "Bash(npm *)",
    "Bash(sh *)",
    "Bash(bash *)",
    "Bash(python *)",
    "Bash(node *)",
}

# Secret patterns to replace
SECRET_REPLACEMENTS = [
    (r'"(AKIA[0-9A-Z]{16})"', "AWS_ACCESS_KEY_ID"),
    (r'"(sk-[a-zA-Z0-9]{20,})"', "API_SECRET_KEY"),
    (r'"(ghp_[a-zA-Z0-9]{36})"', "GITHUB_TOKEN"),
    (r'"(gho_[a-zA-Z0-9]{36})"', "GITHUB_OAUTH_TOKEN"),
    (r'"(xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{24})"', "SLACK_BOT_TOKEN"),
    (r'"(sk_live_[a-zA-Z0-9]{24,})"', "STRIPE_SECRET_KEY"),
]


def harden_settings(settings_path: Path, dry_run: bool, auto: bool) -> list[str]:
    """Harden settings.json permissions."""
    changes = []

    try:
        data = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"  Warning: Could not read {settings_path}: {e}")
        return changes

    modified = False
    permissions = data.setdefault("permissions", {})
    allow_list = permissions.get("allow", [])
    deny_list = permissions.get("deny", [])

    # Remove dangerous wildcards from allow list
    dangerous_found = [a for a in allow_list if a in DANGEROUS_ALLOWS]
    if dangerous_found:
        for item in dangerous_found:
            msg = f"Remove wildcard permission: {item}"
            if auto or (not dry_run and confirm(msg)):
                allow_list.remove(item)
                changes.append(f"Removed: {item} from allow list")
                modified = True
            elif dry_run:
                changes.append(f"[DRY RUN] Would remove: {item} from allow list")

    # Add deny list if missing
    if allow_list and not deny_list:
        msg = "Add default deny list for destructive commands"
        if auto or (not dry_run and confirm(msg)):
            permissions["deny"] = DEFAULT_DENY_LIST
            changes.append(f"Added deny list with {len(DEFAULT_DENY_LIST)} blocked commands")
            modified = True
        elif dry_run:
            changes.append(f"[DRY RUN] Would add deny list with {len(DEFAULT_DENY_LIST)} entries")

    # Remove sandbox bypass
    if data.get("dangerouslyDisableSandbox"):
        msg = "Remove dangerouslyDisableSandbox flag"
        if auto or (not dry_run and confirm(msg)):
            del data["dangerouslyDisableSandbox"]
            changes.append("Removed dangerouslyDisableSandbox")
            modified = True
        elif dry_run:
            changes.append("[DRY RUN] Would remove dangerouslyDisableSandbox")

    if modified:
        settings_path.write_text(json.dumps(data, indent=2) + "\n")

    return changes


def harden_mcp(mcp_path: Path, dry_run: bool, auto: bool) -> list[str]:
    """Harden MCP server configuration."""
    changes = []

    try:
        data = json.loads(mcp_path.read_text())
    except (OSError, json.JSONDecodeError):
        return changes

    modified = False
    servers = data.get("mcpServers", data)

    for name, config in servers.items():
        if not isinstance(config, dict):
            continue

        # Add missing description
        if not config.get("description"):
            config["description"] = f"MCP server: {name}"
            changes.append(f"Added description to MCP server '{name}'")
            modified = True

        # Replace hardcoded secrets in env
        env = config.get("env", {})
        for env_key, env_val in list(env.items()):
            if not isinstance(env_val, str):
                continue
            for pattern, var_name in SECRET_REPLACEMENTS:
                if re.search(pattern.replace('"', ''), env_val):
                    suggested_var = f"${env_key}" if env_key.isupper() else f"${var_name}"
                    msg = f"Replace hardcoded secret in {name}.env.{env_key} with {suggested_var}"
                    if auto or (not dry_run and confirm(msg)):
                        env[env_key] = suggested_var
                        changes.append(f"Replaced secret in {name}.env.{env_key}")
                        modified = True
                    elif dry_run:
                        changes.append(f"[DRY RUN] Would replace secret in {name}.env.{env_key}")
                    break

    if modified:
        mcp_path.write_text(json.dumps(data, indent=2) + "\n")

    return changes


def harden_claude_md(claude_md: Path, dry_run: bool, auto: bool) -> list[str]:
    """Replace hardcoded secrets in CLAUDE.md with env var references."""
    changes = []

    try:
        content = claude_md.read_text()
    except OSError:
        return changes

    modified_content = content
    for pattern, var_name in SECRET_REPLACEMENTS:
        matches = re.findall(pattern, content)
        for match in matches:
            replacement = f'"${var_name}"'
            msg = f"Replace hardcoded secret ({var_name}) in CLAUDE.md"
            if auto or (not dry_run and confirm(msg)):
                modified_content = modified_content.replace(f'"{match}"', replacement)
                changes.append(f"Replaced {var_name} in CLAUDE.md")
            elif dry_run:
                changes.append(f"[DRY RUN] Would replace {var_name} in CLAUDE.md")

    if modified_content != content:
        claude_md.write_text(modified_content)

    return changes


def confirm(message: str) -> bool:
    """Ask user for confirmation."""
    response = input(f"  Apply: {message}? [y/N] ").strip().lower()
    return response in ("y", "yes")


def main():
    parser = argparse.ArgumentParser(description="Harden AI agent configurations")
    parser.add_argument("path", nargs="?", default=".", help="Project directory")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--auto", action="store_true", help="Apply all changes without confirmation")
    args = parser.parse_args()

    project = Path(args.path).resolve()
    if not project.exists():
        print(f"Error: {project} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"\nHardening agent configuration in: {project}")
    if args.dry_run:
        print("  Mode: DRY RUN (no changes will be made)\n")
    elif args.auto:
        print("  Mode: AUTO (all safe fixes applied automatically)\n")
    else:
        print("  Mode: INTERACTIVE (confirm each change)\n")

    all_changes = []

    # Harden settings.json
    claude_dir = project / ".claude"
    settings = claude_dir / "settings.json"
    if settings.exists():
        print(f"  Scanning {settings}...")
        all_changes.extend(harden_settings(settings, args.dry_run, args.auto))

    # Harden MCP config
    for mcp_name in ["mcp.json", "mcp_servers.json"]:
        mcp_path = claude_dir / mcp_name
        if mcp_path.exists():
            print(f"  Scanning {mcp_path}...")
            all_changes.extend(harden_mcp(mcp_path, args.dry_run, args.auto))

    # Harden CLAUDE.md
    claude_md = project / "CLAUDE.md"
    if claude_md.exists():
        print(f"  Scanning {claude_md}...")
        all_changes.extend(harden_claude_md(claude_md, args.dry_run, args.auto))

    # Summary
    print(f"\n{'=' * 50}")
    if all_changes:
        print(f"  Changes {'proposed' if args.dry_run else 'applied'}: {len(all_changes)}")
        for change in all_changes:
            print(f"    - {change}")
    else:
        print("  No changes needed — configuration is already hardened.")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
