# Reference Implementation: `lazboy-brand`

This document walks through the `lazboy-brand` skill as a worked example of the
La-Z-Boy skill standard. Use it as a model when building new skills.

---

## Why `lazboy-brand` is a good reference

- It has a real, well-defined purpose (brand consistency across all agent outputs)
- It uses all the standard folders correctly
- The SKILL.md is comprehensive but under 500 lines
- References are properly separated by topic
- The description is specific enough to trigger reliably

---

## Annotated Structure

```
lazboy-brand/
├── SKILL.md              ← Core instructions (colors, fonts, logo, CSS vars)
├── references/
│   ├── colors.md         ← Full Pantone/CMYK/RGB specs + accessibility notes
│   └── logo-assets.md    ← Logo variants, file formats, sourcing rules
└── assets/               ← (reserved for brand tokens, templates — future)
```

**Why no `scripts/` folder?**
Brand guidelines are mostly reference knowledge, not automation. Scripts would be
added if we wanted agents to *validate* brand usage (e.g., scan a codebase for
off-brand hex values). That's a future enhancement.

**Why are `colors.md` and `logo-assets.md` separate?**
Single responsibility — one topic per file. An agent doing print production needs
`colors.md` (CMYK values). An agent sourcing a logo file needs `logo-assets.md`.
They never need both at the same time, so keeping them separate avoids loading
unnecessary context.

---

## Annotated SKILL.md Frontmatter

```yaml
---
name: lazboy-brand                          # kebab-case, unique in org
description: >
  Apply La-Z-Boy brand standards for any   # What it does
  design, UI, document, or marketing output.
  Use this skill whenever creating or      # When to use it (explicit)
  reviewing anything visual for La-Z-Boy —
  including agent-generated UIs,           # Specific contexts listed
  presentations, reports, emails...
  Trigger on keywords like: "La-Z-Boy      # Trigger keywords
  style", "brand guidelines", "company
  colors", "official font"...
---
```

Key things to notice:
- Description covers both *what* (apply brand standards) and *when* (any visual output)
- Lists specific trigger keywords agents will recognize
- Explicit about edge cases ("even if the user says 'use our brand'")

---

## Annotated SKILL.md Body Sections

### Section 1–2: Core knowledge (Logo, Colors)
The essential facts every agent needs. Kept in SKILL.md because agents need
this for almost every brand task.

### Section 3: Typography
Includes fallbacks — critical because agents can't always use the primary font.
Good skills anticipate failure cases.

### Section 4: Brand Voice
Often overlooked, but important. Agents writing copy need tone guidance, not
just visual specs.

### Section 5: Applying the Brand in Agent Outputs
**This is the most valuable section.** It translates brand rules into
agent-executable formats:
- Ready-to-paste CSS variables
- Specific guidance per output type (HTML, DOCX, PPTX, email)

Without this section, an agent knows the brand but doesn't know how to apply it.
Always include an "applying" section in your skills.

### Section 6: What NOT to Do
Explicit prohibitions. Agents are good at following rules but need
clear "never do this" statements to avoid common mistakes.

### Section 7: Resources
Pointers to reference files with guidance on *when* to read them.
Don't just list files — tell the agent what situation triggers reading each one.

---

## What Could Be Improved

As a living example, here's what `lazboy-brand` v2 might add:

1. **`scripts/validate_brand.py`** — scan a CSS/HTML file and flag off-brand colors
2. **`assets/brand-tokens.json`** — design tokens for Tailwind config or Figma
3. **`assets/email-template.html`** — base HTML email with brand variables applied
4. **More specific HEX values** for the 2025 refresh palette (currently inferred)

These would make the skill more actionable for coding agents doing UI work.
