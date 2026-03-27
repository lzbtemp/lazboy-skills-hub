# La-Z-Boy Logo Asset Reference

All logo files must be sourced from: https://brandguidelines.la-z-boy.com/
Primary logo page: https://brandguidelines.la-z-boy.com/89f81758c/p/73dcba-primary-logo
Contact La-Z-Boy Marketing for access credentials or asset requests.

---

## Table of Contents
1. [How to Get the Logo](#1-how-to-get-the-logo)
2. [Approved Logo Variants](#2-approved-logo-variants)
3. [Tagline Rules](#3-tagline-rules)
4. [Clearspace & Sizing](#4-clearspace--sizing)
5. [Placement Rules](#5-placement-rules)
6. [File Formats](#6-file-formats)
7. [Logo Don'ts](#7-logo-donts)

---

## 1. How to Get the Logo

**IMPORTANT:** Never recreate the logo as SVG text, CSS, or code. Always download the official asset.

**Primary logo (Navy/Comfort Blue) — direct CDN URL:**
```
https://cdn.zeroheight.com/styleguide_logos/131371-default/f9321cebdcd8f9443e8e5a42_LaZboy_2024_Logo_Navy_PMS2189_RGB.png
```
> Note: This URL requires a signed policy token. Visit https://brandguidelines.la-z-boy.com/89f81758c/p/73dcba-primary-logo in a browser to get the current signed URL, then download using `curl`.

**Steps to download the logo for a project:**
1. Open https://brandguidelines.la-z-boy.com/89f81758c/p/73dcba-primary-logo in a browser
2. The page loads the logo with a time-limited signed URL from the CDN
3. Right-click the logo → Save Image As → save as `lazboy-logo.png`
4. Place the file in your project's public/static assets directory (e.g., `public/lazboy-logo.png`)
5. Reference it via `<img src="/lazboy-logo.png" alt="La-Z-Boy" />`

**For white/reversed logo on dark backgrounds:**
Use CSS `brightness-0 invert` (or Tailwind `brightness-0 invert`) on the Navy logo PNG:
```html
<img src="/lazboy-logo.png" alt="La-Z-Boy" class="brightness-0 invert" />
```

**For reduced emphasis (e.g., footer):**
```html
<img src="/lazboy-logo.png" alt="La-Z-Boy" class="brightness-0 invert opacity-40" />
```

---

## 2. Approved Logo Variants

| Variant                  | When to use                                          |
|--------------------------|------------------------------------------------------|
| Full color (primary)     | Default for all digital and print use                |
| One-color: Comfort Blue  | On white or light backgrounds (Warm White, etc.)     |
| One-color: Black         | Single-color print, embossing, engraving, stamping   |
| One-color: White         | Reversed — on Comfort Blue or dark backgrounds only  |

Never create your own variant. Always use an approved file from the brand portal.

---

## 2. Tagline Rules

**Only approved tagline:** `Live life comfortably.®`

- Always include the registered trademark symbol ®
- Sentence case only — never ALL CAPS, Title Case, or italics only
- Never paraphrase, shorten, translate, or reword
- In digital UI: render as plain text using brand typography — do not use the handwritten script version unless using the official approved asset
- The handwritten script version is a specific marketing asset — request it from Marketing, never substitute with a generic script or cursive font

---

## 4. Clearspace & Sizing

**Clearspace:** Maintain clearspace equal to the height of the capital "L" in the wordmark on all four sides. No other graphic elements, text, or imagery may appear within this zone.

**Minimum sizes:**
- Digital: 72px wide
- Print: 1 inch (25.4mm) wide
- Never scale below these thresholds — legibility and brand integrity require it

---

## 5. Placement Rules

- Place on backgrounds with sufficient contrast (see colors.md for contrast ratios)
- Do not place on busy photographic backgrounds without a clear/solid color bar behind the logo
- Preferred placements: top-left (web headers), centered (title slides, email headers)
- Always align to a grid — never float the logo at arbitrary positions

---

## 6. File Formats

Request these formats from Marketing depending on your use case:

| Format       | Use case                                              |
|--------------|-------------------------------------------------------|
| `.SVG`       | Web, scalable UI, any digital use at any size         |
| `.PNG` (transparent bg) | Documents, slide decks, email headers     |
| `.EPS`       | Print production, large-format, vendor handoffs       |
| `.AI`        | Design editing in Adobe Illustrator                   |
| `.PDF`       | High-res print when EPS is unavailable               |

Never export or save your own version of the logo from a document. Always use the original asset file.

---

## 7. Logo Don'ts

1. ❌ Do not recolor outside approved variants
2. ❌ Do not add drop shadows, glows, gradients, or any effects
3. ❌ Do not stretch, skew, or distort the proportions
4. ❌ Do not place on low-contrast or busy backgrounds without a backing
5. ❌ Do not recreate the logo in CSS, SVG paths, or any code — always use the official asset
6. ❌ Do not use below minimum size (72px digital / 1in print)
7. ❌ Do not use an outdated logo version — always pull from the brand portal
8. ❌ Do not add the tagline next to the logo unless the approved lockup file includes it
