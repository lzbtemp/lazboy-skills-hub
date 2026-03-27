# La-Z-Boy Typography Reference

Extended font documentation for web setup, licensing, and pairing rules.

---

## Table of Contents
1. [Font Licensing](#1-font-licensing)
2. [Web Font Setup](#2-web-font-setup)
3. [Font Pairing Rules](#3-font-pairing-rules)
4. [Usage by Medium](#4-usage-by-medium)
5. [Legacy Whitney Reference](#5-legacy-whitney-reference)

---

## 1. Font Licensing

### Helvetica Neue
- **Type:** Licensed commercial font (Linotype)
- **Purchase:** fonts.com or call 1-800-424-8973
- **Required weights:** 400 (Regular), 500 (Medium), 600 (Semi-Bold), 700 (Bold)
- **Desktop license:** Covers use in DOCX, PPTX, print PDFs
- **Web license:** Separate license required for CSS @font-face embedding
- **Alternative if unlicensed:** Use system fallback stack (Helvetica → Arial)

### Handwritten Tagline Script
- Proprietary asset — not available for purchase externally
- Request file from La-Z-Boy Marketing for approved use cases only
- Do not substitute with any commercial or free script font

---

## 2. Web Font Setup

### Option A: Licensed Helvetica Neue via fonts.com CDN
```html
<link rel="stylesheet" href="https://fast.fonts.net/[your-project-id]/css/[font-id].css">
```
Contact Marketing for the project-specific CDN link.

### Option B: System font stack (no license required)
```css
body {
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```
This is the approved fallback for all web projects where the licensed font is not available.

### Option C: Google Fonts approximation (internal/prototype only)
For internal tools and prototypes only — not for customer-facing materials:
```css
/* Closest Google Fonts approximation */
@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700&display=swap');
/* Use only until Helvetica Neue license is in place */
```

---

## 3. Font Pairing Rules

### Approved pairings
| Heading font          | Body font              | Use case                    |
|-----------------------|------------------------|-----------------------------|
| Helvetica Neue Bold   | Helvetica Neue Regular | All standard brand materials|
| Helvetica Neue Bold   | Arial Regular          | Fallback (PC/no license)    |

### Never pair with
- Serif fonts (Times New Roman, Georgia) — conflicts with brand's modern/clean aesthetic
- Display or decorative fonts (except the official tagline script asset)
- Multiple sans-serif families in the same document

### Weight usage rules
- Use Bold (700) for headings only — never for body text
- Use Semi-Bold (600) for subheadings and UI labels
- Use Regular (400) for all body copy — never use Light (300) for body text (too thin on screen)
- Use Medium (500) sparingly — for callouts or emphasized UI text only

---

## 4. Usage by Medium

### Web / Digital
- Apply CSS custom property `--font-stack` from SKILL.md Section 5
- Enable antialiasing: `-webkit-font-smoothing: antialiased`
- Line height for body: 1.6 (generous, comfortable — reflects brand warmth)
- Letter spacing for headings: -0.02em (slightly tighter for large display text)

### Print / DOCX
- Embed fonts when saving PDFs for external distribution
- If recipient doesn't have Helvetica Neue, Arial will auto-substitute — acceptable fallback
- Minimum print body size: 9pt

### Presentations / PPTX
- Set Helvetica Neue as theme font in PowerPoint (Design → Fonts → Customize)
- If sharing externally, embed fonts: File → Options → Save → Embed fonts

### Email HTML
- Always use web-safe fallback stack — email clients don't support custom fonts
- `font-family: Helvetica, Arial, sans-serif;` for all email typography

---

## 5. Legacy Whitney Reference

Some older corporate documents use the Whitney font system. Do not use for new work.

| Element     | Whitney Weight  | Size     |
|-------------|-----------------|----------|
| Headers     | Whitney Semi Bold | varies |
| Subheaders  | Whitney Semi Bold | varies |
| Body text   | Whitney Book    | varies   |
| Fallback    | Helvetica (Mac) / Arial (PC) | — |

If maintaining an older document in Whitney, do not switch mid-document to Helvetica Neue — keep consistency within the document.
