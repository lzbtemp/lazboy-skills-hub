---
name: lazboy-brand
description: "Apply La-Z-Boy brand standards for any design, UI, document, or marketing output. Use this skill whenever creating or reviewing anything visual or written for La-Z-Boy — including agent-generated UIs, presentations, reports, emails, code with style notes, or any artifact that must match the official La-Z-Boy look and feel. Trigger on: La-Z-Boy style, brand guidelines, company colors, official font, logo usage, brand-compliant, on-brand, use our brand, or any request to create a file (docx, pptx, html, jsx, css) for La-Z-Boy internal or external use. Also trigger when generating React components, HTML pages, slide decks, or email templates for La-Z-Boy — even if the user doesn't explicitly mention brand guidelines."
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
- **NEVER recreate the logo as SVG text, CSS, or code** — always download the official asset
- Download from: https://brandguidelines.la-z-boy.com/89f81758c/p/73dcba-primary-logo
- Save as `lazboy-logo.png` in the project's public/static assets directory
- Reference via `<img src="/lazboy-logo.png" alt="La-Z-Boy" />`
- For white/reversed on dark backgrounds: add CSS `brightness-0 invert`
- Use approved one-color variants (Comfort Blue or Black) when full color isn't available
- Maintain clearspace equal to the height of the "L" on all sides
- Minimum size: 72px wide (digital) / 1 inch wide (print)
- Recommended sizes: header `h-10` (40px height), footer `h-8` (32px height)
- Do NOT place the logo in hero banners — it duplicates the header logo

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

These guidelines ensure La-Z-Boy digital outputs feel polished, distinctive, and intentional — not generic or cookie-cutter. Apply brand colors and typography as defined above, but use these techniques to elevate the execution.

### Design Thinking (before coding)
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: La-Z-Boy's aesthetic direction is **luxury editorial** — clean but warm, confident whitespace, dramatic type scale, rich micro-interactions, and atmospheric depth. Think high-end furniture catalog meets modern SaaS dashboard.
- **Differentiation**: What makes this memorable? Every La-Z-Boy UI should feel crafted, not templated.

### Motion & Animation
- **Orchestrate page load**: Use staggered `animation-delay` for a cascading reveal effect. One well-orchestrated entrance creates more impact than scattered micro-interactions.
- **Hover states**: Cards and interactive elements should respond with lift (`translateY(-3px)`), shadow deepening, and color transitions. Use `cubic-bezier(0.22, 1, 0.36, 1)` for smooth, spring-like easing.
- **Scroll-triggered reveals**: Use Intersection Observer to animate sections into view as the user scrolls — not all at once on mount.
- **Transitions**: All interactive state changes (hover, focus, active) should have `transition` — never abrupt jumps. 200–300ms is the sweet spot.
- **Restraint**: Match animation complexity to the context. Internal tools need subtle polish, not pyrotechnics.

### Shadows & Depth
Use brand-colored shadows instead of generic gray:
```css
--shadow-card:       0 1px 3px rgba(27, 58, 107, 0.04), 0 1px 2px rgba(27, 58, 107, 0.02);
--shadow-card-hover: 0 20px 40px -12px rgba(27, 58, 107, 0.15), 0 8px 16px -8px rgba(27, 58, 107, 0.08);
--shadow-glow:       0 0 40px -8px rgba(27, 58, 107, 0.12);
```
Shadows should use Comfort Blue (`#1B3A6B`) at low opacity, not black or gray. This creates a cohesive, branded depth effect.

### Backgrounds & Atmosphere
- **Never default to flat solid colors** — use gradients within the brand palette (e.g., `from-[#1B3A6B] via-[#152f58] to-[#0f2140]` for hero sections)
- **Noise/grain textures**: Subtle SVG noise overlays at 2–4% opacity add tactile warmth that echoes the furniture brand
- **Geometric patterns**: Dot grids, circles, or rounded rectangles at very low opacity (3–6%) create visual interest without distraction
- **Glass-morphism**: `backdrop-blur` with semi-transparent brand colors works well for overlays, search bars, and floating elements on dark backgrounds

### Spatial Composition & Layout
- **Prefer asymmetric hero layouts** — split content (text left, visual right) over centered text blocks
- **Generous negative space**: La-Z-Boy's comfort identity should breathe. Use `py-16 lg:py-20` or more for sections, not cramped `py-8`
- **Decorative accents**: Gradient lines, accent stripes (thin gradient bar at card tops), and angled clip-path edges add editorial polish
- **Grid-breaking moments**: Feature a hero card spanning 2 columns, or use offset positioning to break strict grid monotony

### Typography Expressiveness
While Helvetica Neue is mandatory, maximize its range:
- **Dramatic scale contrast**: Hero headings at `text-6xl lg:text-7xl` with `tracking-tight leading-[0.95]` feel editorial, not generic
- **Weight contrast**: Bold (700) headings against Light/Regular (300/400) body text creates strong visual hierarchy
- **Letter-spacing variety**: `tracking-tight` for large display text, `tracking-[0.15em] uppercase` for small labels and section headers
- **Font size tokens should use `clamp()`** for fluid responsive scaling

### Anti-Patterns to Avoid
- ❌ Flat, evenly-spaced grids with no visual hierarchy
- ❌ Cards that all look identical — vary treatments for featured vs. regular items
- ❌ Generic gray shadows (`rgba(0,0,0,0.1)`) — always use brand-colored shadows
- ❌ Abrupt state changes without transitions
- ❌ Cookie-cutter layouts that feel AI-generated — every page should feel intentionally designed
- ❌ Timid color application — be confident with Comfort Blue and use Burnt Vermilion as a sharp accent, not sprinkled everywhere equally

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
- Consult the `docx` skill for file creation
- Heading 1/2: Comfort Blue (`#1B3A6B`), Helvetica Neue Bold
- Body: Charcoal (`#2C2C2C`), Helvetica Neue Regular
- Background: Warm White pages
- Accent lines / callout boxes: Burnt Vermilion (`#C0392B`) border, sparingly

### PPTX / Presentations
- Consult the `pptx` skill for file creation
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
| Logo variants and file sourcing | `references/logo-assets.md` | Any time you need to place a logo |
| Font licensing and web setup | `references/typography.md` | Setting up a new web project or doc template |
| Design tokens (JSON) | `assets/brand-tokens.json` | Tailwind config, Figma, Style Dictionary |
| React base component | `assets/component-base.tsx` | Starting any new React UI |
| Email base template | `assets/email-template.html` | Building HTML emails |
| Color/font validator | `scripts/validate_brand.py` | Checking any CSS or HTML file |
| Token generator | `scripts/generate_tokens.py` | Exporting tokens in a new format |
| Official brand portal | https://brandguidelines.la-z-boy.com/ | Logo files, latest guidelines |
