---
name: lazboy-brand
description: "Apply La-Z-Boy brand standards for any design, UI, document, or marketing output. Use this skill whenever creating or reviewing anything visual or written for La-Z-Boy — including agent-generated UIs, presentations, reports, emails, code with style notes, or any artifact that must match the official La-Z-Boy look and feel. Trigger on: La-Z-Boy style, brand guidelines, company colors, official font, logo usage, brand-compliant, on-brand, use our brand, or any request to create a file (docx, pptx, html, jsx, css) for La-Z-Boy internal or external use. Also trigger when generating React components, HTML pages, slide decks, or email templates for La-Z-Boy — even if the user doesn't explicitly mention brand guidelines."
version: "1.0.0"
category: Designer
tags: [designer, brand, ui, design-system, style-guide]
---

# La-Z-Boy Brand Skill

Ensures all agent outputs are consistent with La-Z-Boy's official brand identity.
Always apply this skill before producing any visual or written deliverable for La-Z-Boy.

**Official brand portal:** https://brandguidelines.la-z-boy.com/
**Questions / approvals:** Contact La-Z-Boy Marketing

**Reference files — load when needed:**
- `references/colors.md` — full Pantone, CMYK, RGB specs + WCAG accessibility notes
- `references/logo-assets.md` — logo variants, file formats, sourcing rules
- `references/typography.md` — extended font licensing, pairing rules, web font setup

**Scripts — run when needed:**
- `scripts/validate_brand.py` — scan a CSS/HTML file and flag off-brand colors or fonts
- `scripts/generate_tokens.py` — output brand design tokens as CSS, JSON, or Tailwind config

**Assets — use as base templates:**
- `assets/logos/` — official logo files in multiple sizes (copy into your project)
- `assets/brand-tokens.json` — design tokens ready for Tailwind / Figma / Style Dictionary
- `assets/component-base.tsx` — React component with all brand variables pre-applied
- `assets/email-template.html` — pre-styled HTML email base

---

## 1. Logo

**The wordmark** uses a custom italic rounded typeface (2025 brand refresh by Colle McVoy).
Every letterform is rounded and slightly reclined — echoing the comfort and recliner identity.
The distinctive "L", "Z", and hyphens are signature elements and must never be altered.

**Only approved tagline:** `Live life comfortably.®`
- Always include the ® symbol
- Sentence case only — never ALL CAPS or altered wording

**Logo usage rules**
- **Never recreate the logo as SVG text, CSS, or code** — handcrafted reproductions always drift from the approved wordmark geometry, and code-generated logos create legal risk around trademark accuracy. Always use the bundled asset files.
- **Logo files are available via GitHub raw URL.** Do NOT use read/write tools to copy PNGs — binary files get corrupted. Instead, use a shell command:
  ```bash
  # Standard web header (400w) — recommended for most projects
  curl -sL "https://raw.githubusercontent.com/lzbtemp/lazboy-agent-skills/main/skills/lazboy-brand/assets/logos/lazboy-logo-navy-400w.png" -o public/lazboy-logo.png

  # Compact (200w) — for sidebar, footer
  curl -sL "https://raw.githubusercontent.com/lzbtemp/lazboy-agent-skills/main/skills/lazboy-brand/assets/logos/lazboy-logo-navy-200w.png" -o public/lazboy-logo.png

  # Full resolution (3168x1129) — for print/high-DPI
  curl -sL "https://raw.githubusercontent.com/lzbtemp/lazboy-agent-skills/main/skills/lazboy-brand/assets/logos/lazboy-logo-navy.png" -o public/lazboy-logo.png

  # Small badge (80w)
  curl -sL "https://raw.githubusercontent.com/lzbtemp/lazboy-agent-skills/main/skills/lazboy-brand/assets/logos/lazboy-logo-navy-80w.png" -o public/lazboy-logo.png
  ```
- **IMPORTANT:** Always use `curl`, `cp`, or `wget` to copy logo files. Never use file read/write tools — they corrupt binary PNG data.
- Adjust the output path (`public/`, `static/`, `src/assets/`) to match your project structure
- Reference via `<img src="/lazboy-logo.png" alt="La-Z-Boy" />`
- For white/reversed on dark backgrounds: add CSS `brightness-0 invert`
- Use approved one-color variants (Comfort Blue or Black) when full color isn't available
- Maintain clearspace equal to the height of the "L" on all sides
- Minimum size: 72px wide (digital) / 1 inch wide (print)
- Recommended sizes: header `h-10` (40px height), footer `h-8` (32px height)
- Do NOT place the logo in hero banners — it duplicates the header logo
- Do NOT repeat the logo in the footer — keep it in the header only

### Favicon
Use the official La-Z-Boy favicon from the corporate site:
```bash
curl -sL "https://www.la-z-boy.com/favicon.ico" -o public/favicon.ico
```
Reference in HTML:
```html
<link rel="icon" type="image/x-icon" href="/favicon.ico" />
```

> Read `references/logo-assets.md` for download steps, approved variants, file formats, and how to request assets from Marketing.

---

## 2. Color Palette

### Primary Palette (2025 Brand Refresh)

| Name            | HEX       | Role                          |
|-----------------|-----------|-------------------------------|
| Comfort Blue    | `#1B3A6B` | Logo, headings, hero bg, nav  |
| Burnt Vermilion | `#C0392B` | Accent, CTAs, dividers        |
| Soft Celadon    | `#8FAF8A` | Secondary accent, calm themes |
| Warm White      | `#FAF8F5` | Page/slide backgrounds        |
| Charcoal        | `#2C2C2C` | Body text, captions           |

### Legacy Corporate Colors (still approved)

| Name         | HEX       | Usage                          |
|--------------|-----------|--------------------------------|
| La-Z-Boy Red | `#CC0000` | Older corporate materials only |
| White        | `#FFFFFF` | Reversed text on dark bg       |
| Black        | `#000000` | One-color logo, fine print     |

**Default combination:** Comfort Blue + Warm White background + Burnt Vermilion accent.
Prefer the 2025 palette for all new work. Use legacy colors only when matching existing materials.

> Read `references/colors.md` for Pantone, CMYK, RGB values and WCAG accessibility ratings.

---

## 3. Typography

### Primary: Helvetica Neue Family

| Use           | Weight         | Size       |
|---------------|----------------|------------|
| H1 Display    | Bold (700)     | 32–48px    |
| H2 Heading    | Bold (700)     | 24–32px    |
| H3 Subheading | Semi-Bold (600)| 18–22px    |
| Body copy     | Regular (400)  | 14–16px    |
| Caption       | Regular (400)  | 12px       |

**Color:** H1/H2 in Comfort Blue or Charcoal. H3/Body/Caption in Charcoal.
**Purchase:** fonts.com | 1-800-424-8973

### Fallbacks (when Helvetica Neue is unavailable)
```css
font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
```
- Mac: Helvetica
- PC / web: Arial

### Handwritten accent (tagline only)
The tagline uses a custom handwritten script in some marketing contexts.
Never substitute with a generic script font — use only the official asset file from Marketing.

### Legacy: Whitney (older corporate docs only)
- Whitney Book → paragraph text
- Whitney Semi Bold → headers and subheaders
- Fallback: Helvetica / Arial

> Read `references/typography.md` for font licensing details, web font CDN setup, and pairing rules.

---

## 4. Brand Voice & Tone

- **Warm and inviting** — every touchpoint should feel like sinking into a favorite chair
- **Comfortable, not casual** — professional but never stiff or corporate
- **Nostalgic yet modern** — rooted in 1927 heritage, forward-looking in experience
- **Calm and unhurried** — avoid urgency language, excessive punctuation, pushy sales tone

**Word choices to prefer:** comfort, ease, quality, crafted, lasting, home, warmth
**Word choices to avoid:** revolutionary, disruptive, best-in-class, synergy, leverage

---

## 5. Design Quality Standards

La-Z-Boy's aesthetic direction is **luxury editorial** — clean but warm, confident whitespace, dramatic type scale, and atmospheric depth. Think high-end furniture catalog meets modern SaaS dashboard. Every output should feel crafted, not templated.

**Core principles:**
- Use brand-colored shadows (Comfort Blue at low opacity), never generic gray
- Use gradients and subtle textures — never flat solid backgrounds
- Animate all interactive state changes (200–300ms) — abrupt jumps break the comfort feeling
- Give layouts room to breathe — generous spacing echoes the brand identity

> Read `references/design-quality.md` for detailed patterns on motion, shadows, backgrounds, layout composition, and typography — especially when building hero sections, dashboards, or any polished UI.

---

## 6. Applying the Brand in Agent Outputs

### HTML / CSS / Web UI
```css
:root {
  /* Colors */
  --color-primary:     #1B3A6B; /* Comfort Blue */
  --color-accent:      #C0392B; /* Burnt Vermilion */
  --color-green:       #8FAF8A; /* Soft Celadon */
  --color-bg:          #FAF8F5; /* Warm White */
  --color-text:        #2C2C2C; /* Charcoal */
  --color-text-light:  rgba(44, 44, 44, 0.6);
  --color-white:       #FFFFFF;

  /* Typography */
  --font-stack:        'Helvetica Neue', Helvetica, Arial, sans-serif;
  --font-size-h1:      clamp(32px, 5vw, 48px);
  --font-size-h2:      clamp(24px, 4vw, 32px);
  --font-size-h3:      20px;
  --font-size-body:    15px;
  --font-size-caption: 12px;

  /* Spacing */
  --radius-sm:         4px;
  --radius-md:         8px;
  --radius-lg:         16px; /* Prefer rounded corners — echoes cushioned furniture */

  /* Shadows (brand-colored) */
  --shadow-card:       0 1px 3px rgba(27, 58, 107, 0.04), 0 1px 2px rgba(27, 58, 107, 0.02);
  --shadow-card-hover: 0 20px 40px -12px rgba(27, 58, 107, 0.15), 0 8px 16px -8px rgba(27, 58, 107, 0.08);
  --shadow-glow:       0 0 40px -8px rgba(27, 58, 107, 0.12);
}
```

Use `assets/component-base.tsx` as the starting point for any React component.

### React / JSX
- Import and use CSS variables above — never hardcode hex values inline
- Prefer rounded corners (`border-radius: var(--radius-md)`) — echoes the furniture aesthetic
- Use `assets/component-base.tsx` as your base
- Apply motion and depth guidelines from Section 5 — every component should feel polished

### DOCX / Word Documents
Use `python-docx` or the available file-creation tool. Apply these styles:
- Heading 1/2: Comfort Blue (`#1B3A6B`), Helvetica Neue Bold
- Body: Charcoal (`#2C2C2C`), Helvetica Neue Regular
- Background: Warm White pages
- Accent lines / callout boxes: Burnt Vermilion (`#C0392B`) border, sparingly

### PPTX / Presentations
Use `python-pptx` or the available file-creation tool. Apply these styles:
- Title slides: Comfort Blue background, white title text
- Content slides: Warm White background, Comfort Blue headings
- Max 2 accent colors per slide
- Use Burnt Vermilion for emphasis — never as background color

### Email Templates
- Use `assets/email-template.html` as the base
- Header bar: Comfort Blue (`#1B3A6B`)
- CTA buttons: Burnt Vermilion (`#C0392B`), white label text, 4px border-radius
- Footer: Charcoal text on Warm White background
- Max width: 600px

### Footer
Keep footers minimal — do not duplicate navigation links already in the header/nav.
```
Pattern: Copyright (left) | Social icons (right)
```
- Background: Comfort Blue (`#1B3A6B`)
- Text: `text-sm text-white/80` for copyright
- Social icons: `w-5 h-5 text-white/50 hover:text-white` with SVG icons for Facebook, Instagram, Pinterest
- Do NOT include the logo in the footer
- Do NOT add link columns (Explore, Resources, etc.) — these duplicate the main navigation
- Do NOT include the tagline in the footer

### Design Tokens (Tailwind / Figma / Style Dictionary)
- Use `assets/brand-tokens.json` — import directly into your config
- Run `scripts/generate_tokens.py` to regenerate tokens in any format

---

## 7. What NOT to Do

- ❌ Never hardcode hex values — always use CSS variables or tokens
- ❌ Never use pure white (`#FFFFFF`) as a page/slide background — use Warm White (`#FAF8F5`)
- ❌ Never use a font other than Helvetica Neue (or its approved fallbacks)
- ❌ Never recreate the logo in CSS, SVG code, or any other medium — always use the official asset file
- ❌ Never distort, recolor, add effects, or drop shadows to the wordmark
- ❌ Never use the tagline in any form other than `Live life comfortably.®`
- ❌ Never use Burnt Vermilion + Soft Celadon as the dominant color pair — too much contrast
- ❌ Never use Soft Celadon for body text — it fails WCAG AA accessibility on white backgrounds
- ❌ Never use legacy La-Z-Boy Red (`#CC0000`) for new work — use Burnt Vermilion (`#C0392B`)

---

## 8. Brand Validation

Before delivering any branded output, run the validator:

```bash
python scripts/validate_brand.py path/to/your/file.css
python scripts/validate_brand.py path/to/your/file.html
```

It will flag: off-brand hex values, non-approved fonts, missing CSS variables.

---

## 9. Resources

| Resource | Path | When to use |
|----------|------|-------------|
| Full color specs (Pantone, CMYK, WCAG) | `references/colors.md` | Print production, accessibility review |
| Logo files (multiple sizes) | `assets/logos/` | Copy into your project's public directory |
| Logo variants and file sourcing | `references/logo-assets.md` | Any time you need to place a logo |
| Font licensing and web setup | `references/typography.md` | Setting up a new web project or doc template |
| Design tokens (JSON) | `assets/brand-tokens.json` | Tailwind config, Figma, Style Dictionary |
| React base component | `assets/component-base.tsx` | Starting any new React UI |
| Email base template | `assets/email-template.html` | Building HTML emails |
| Color/font validator | `scripts/validate_brand.py` | Checking any CSS or HTML file |
| Token generator | `scripts/generate_tokens.py` | Exporting tokens in a new format |
| Official brand portal | https://brandguidelines.la-z-boy.com/ | Logo files, latest guidelines |
