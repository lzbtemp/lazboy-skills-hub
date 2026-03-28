---
name: lazboy-skill-standard
description: "The La-Z-Boy organization standard for creating, structuring, and maintaining agent skills. Use this skill whenever creating a new skill, reviewing an existing skill, onboarding a new skill author, or auditing the skill library for consistency — even if the user doesn't explicitly say 'skill'. Trigger on: create a skill, new skill, skill template, skill standard, how do I write a skill, skill review, update a skill, add to the skill library, or any time someone is building, improving, or evaluating agent capabilities for La-Z-Boy."
version: "1.0.0"
category: Meta
tags: [meta, skill-authoring, standards, templates]
---

# La-Z-Boy Agent Skill Standard

This document defines how all agent skills at La-Z-Boy must be structured, written, and maintained.
Every skill — whether for brand, code generation, data, or workflows — follows this standard.

**Reference implementation:** `lazboy-brand` skill (see it as a worked example of this standard)
**Skill template:** `assets/skill-template/` (copy this to start any new skill)

---

## 1. Why a Standard?

Skills are the org's institutional knowledge for agents. Without a standard:
- Agents trigger inconsistently — some skills get ignored
- Skill quality varies wildly across teams
- Maintenance becomes hard as the library grows
- New skill authors don't know what "good" looks like

With this standard, every skill is predictable, maintainable, and agent-friendly.

---

## 2. Required Directory Structure

Every La-Z-Boy skill MUST follow this layout:

```
skill-name/
├── SKILL.md              # Required — instructions + YAML metadata
├── scripts/              # Optional — executable automation code
├── references/           # Optional — detailed documentation, specs
└── assets/               # Optional — templates, tokens, static files
```

### Naming conventions
- Skill folder: `kebab-case` (e.g., `lazboy-brand`, `api-codegen`, `data-pipeline`)
- Files inside: `kebab-case.md`, `kebab-case.py`, `kebab-case.json`
- No spaces, no uppercase folder names

---

## 3. SKILL.md Structure

Every `SKILL.md` must contain:

### 3a. YAML Frontmatter (required)
```yaml
---
name: skill-name
description: >
  One paragraph. What does this skill do? When should agents use it?
  Include specific trigger phrases and contexts. Be slightly "pushy" —
  agents tend to undertrigger, so be explicit about when to use this skill.
  Example: "Use this skill whenever the user mentions X, Y, or Z, even if
  they don't explicitly ask for it."
compatibility: "optional — list required tools or dependencies if any"
---
```

**Description writing rules:**
- Include BOTH what the skill does AND when to use it
- List specific trigger keywords/phrases agents should recognize
- Aim for ~75–150 words in the description
- Never put "when to use" information only in the body — it belongs in the description

### 3b. Body (required)
The body is the skill's actual instructions. Structure it with:

```markdown
# Skill Name

One-line summary of what this skill does and why it matters.

## 1. [Core concept or workflow step]
## 2. [Next concept]
## 3. Applying This Skill in Agent Outputs
## 4. What NOT to Do
## 5. Resources & References
```

**Body writing rules:**
- Keep under 500 lines — if longer, move detail into `references/`
- Use imperative form: "Apply X", "Use Y", "Never do Z"
- Explain *why* rules exist, not just what they are
- Always include a "What NOT to Do" section
- End with pointers to any `references/` files and when to read them

---

## 4. The Four Folders — When to Use Each

### `scripts/` — Executable automation
Use for deterministic, repeatable tasks agents should run rather than reason about.

Good examples:
- `validate_colors.py` — checks if HEX values in a file are on-brand
- `generate_tokens.py` — outputs CSS/JSON design tokens from brand specs
- `lint_skill.py` — checks a SKILL.md for standard compliance

Rules:
- Scripts must be runnable standalone (no hidden dependencies)
- Include a docstring explaining what the script does and how to run it
- Output should be human-readable (print results, not just exit codes)

### `references/` — Deep documentation
Use for detailed specs that are too long for SKILL.md but agents need occasionally.

Good examples:
- `colors.md` — full Pantone/CMYK/RGB specs (like in `lazboy-brand`)
- `logo-assets.md` — logo variant rules and file formats
- `api-schema.md` — full API endpoint documentation

Rules:
- Always reference these files from SKILL.md with guidance on when to read them
- Files over 300 lines need a table of contents at the top
- Keep one topic per file — don't mix color specs and typography in one file

### `assets/` — Reusable templates and static files
Use for files agents include or copy into their outputs.

Good examples:
- `brand-tokens.json` — design tokens for Tailwind/CSS
- `email-template.html` — pre-styled HTML email base
- `slide-template.pptx` — branded PowerPoint starter
- `component-base.tsx` — React component with brand variables pre-applied

Rules:
- Assets must be production-ready — agents will use them as-is
- Include a brief README or inline comment explaining the asset's purpose
- Version assets if they change frequently (e.g., `tokens-v2.json`)

---

## 5. Progressive Disclosure — The Three Levels

Skills load in three levels. Design your skill with this in mind:

| Level | What loads | Size target | Always in context? |
|-------|-----------|-------------|-------------------|
| 1 | Frontmatter (name + description) | ~100 words | ✅ Yes |
| 2 | SKILL.md body | < 500 lines | ✅ When triggered |
| 3 | scripts/, references/, assets/ | Unlimited | ❌ On demand only |

**Practical rule:** If something is needed for 80% of uses → put it in SKILL.md.
If it's needed for 20% of specialized uses → put it in `references/` and point to it.

---

## 6. Quality Checklist

Before publishing any skill, verify:

**Metadata**
- [ ] `name` is kebab-case and unique in the org library
- [ ] `description` includes trigger phrases and is 75–150 words
- [ ] `description` says both *what* the skill does and *when* to use it

**SKILL.md body**
- [ ] Under 500 lines
- [ ] Has a "What NOT to Do" section
- [ ] References any `references/` files with guidance on when to read them
- [ ] Uses imperative form ("Apply X", not "You should apply X")
- [ ] Explains *why* rules exist, not just what they are

**Folders**
- [ ] Only contains folders from the standard (scripts/, references/, assets/)
- [ ] No unused empty folders committed (only include folders you've populated)
- [ ] Scripts are runnable standalone
- [ ] Reference files over 300 lines have a table of contents

**Testing**
- [ ] Skill has been tested with at least 2–3 realistic prompts
- [ ] Agent triggered correctly without being explicitly told to use the skill
- [ ] Output matched expected brand/quality standards

---

## 7. Skill Lifecycle

```
Draft → Review → Publish → Maintain → Deprecate
```

- **Draft:** Use `assets/skill-template/` as your starting point
- **Review:** Run through the quality checklist above; have one other person verify
- **Publish:** Install to `.claude/skills/` (per-project) or `~/.claude/skills/` (global)
- **Maintain:** Update when underlying source (brand guidelines, APIs, etc.) changes
- **Deprecate:** Add a `deprecated: true` field to frontmatter and a notice at the top of SKILL.md pointing to the replacement

---

## 8. La-Z-Boy Skill Library

| Skill | Purpose | Owner |
|-------|---------|-------|
| `lazboy-brand` | Brand colors, fonts, logo usage for all agent outputs | Marketing / Design |
| `lazboy-skill-standard` | Org standard for creating and maintaining skills | Engineering |
| `lazboy-python-best-practices` | Python 3.12+ coding standards, tooling, testing patterns | Engineering |
| `lazboy-playwright` | Playwright E2E test writing, POM patterns, CI/CD setup | Engineering / QA |

> Read `references/skill-registry.md` for the full registry with install paths and update history.

---

## Reference Files

- `references/skill-registry.md` — Full org skill library with owners and install paths
- `references/examples.md` — Annotated walkthrough of `lazboy-brand` as a reference implementation
- `assets/skill-template/` — Starter scaffold to copy when creating a new skill
