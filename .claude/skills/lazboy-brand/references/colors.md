# La-Z-Boy Color Reference

Full color specifications for brand-accurate reproduction across all media.
Last updated: 2026-03

## Table of Contents
1. [Primary Palette (2025 Refresh)](#1-primary-palette-2025-refresh)
2. [Legacy Corporate Palette](#2-legacy-corporate-palette)
3. [Color Combinations](#3-color-combinations)
4. [Accessibility (WCAG)](#4-accessibility-wcag)
5. [Usage by Medium](#5-usage-by-medium)

---

## 1. Primary Palette (2025 Refresh)

### Comfort Blue
- HEX: `#1B3A6B`
- RGB: 27, 58, 107
- CMYK: 100, 74, 0, 32
- Pantone: PMS 2756 C (approx)
- HSL: 218°, 60%, 26%
- Usage: Logo, headings, hero backgrounds, nav bars, primary CTA, title slides

### Burnt Vermilion
- HEX: `#C0392B`
- RGB: 192, 57, 43
- CMYK: 0, 70, 78, 25
- Pantone: PMS 7627 C (approx)
- HSL: 5°, 63%, 46%
- Usage: Accent, CTA buttons, divider lines, callout highlights, link hover states

### Soft Celadon
- HEX: `#8FAF8A`
- RGB: 143, 175, 138
- CMYK: 18, 0, 21, 31
- Pantone: PMS 7494 C (approx)
- HSL: 114°, 14%, 61%
- Usage: Secondary accents, nature/calm motifs, subtle background tints, icons
- ⚠️ Decorative use only — does not meet WCAG AA for text (see Section 4)

### Warm White
- HEX: `#FAF8F5`
- RGB: 250, 248, 245
- CMYK: 0, 1, 2, 2
- HSL: 40°, 33%, 97%
- Usage: Page backgrounds, slide backgrounds, light mode UI, email body background
- Note: Always prefer this over pure #FFFFFF — the warmth aligns with brand identity

### Charcoal
- HEX: `#2C2C2C`
- RGB: 44, 44, 44
- CMYK: 0, 0, 0, 83
- HSL: 0°, 0%, 17%
- Usage: Body text, captions, secondary UI elements, footer text

---

## 2. Legacy Corporate Palette

### La-Z-Boy Red (Legacy — do not use for new work)
- HEX: `#CC0000`
- RGB: 204, 0, 0
- CMYK: 0, 100, 100, 20
- Pantone: PMS 186 C
- Usage: Only when matching existing legacy materials; use Burnt Vermilion for all new work

### White
- HEX: `#FFFFFF`
- Usage: Reversed text on Comfort Blue or Charcoal backgrounds; print whites

### Black
- HEX: `#000000`
- Usage: One-color logo applications, fine print, legal text

---

## 3. Color Combinations

### Approved Primary Combinations
| Foreground       | Background      | Use case                        |
|------------------|-----------------|---------------------------------|
| White `#FFFFFF`  | Comfort Blue    | Title slides, hero headers, nav |
| Comfort Blue     | Warm White      | Headings on content pages       |
| Charcoal         | Warm White      | Body text, default UI           |
| White `#FFFFFF`  | Burnt Vermilion | CTA buttons                     |
| Comfort Blue     | White `#FFFFFF` | Inline links, icon labels       |

### Combinations to Avoid
| Combination                          | Reason                             |
|--------------------------------------|------------------------------------|
| Burnt Vermilion + Soft Celadon       | Too much contrast, clashes visually|
| Soft Celadon as text color           | Fails WCAG AA accessibility        |
| La-Z-Boy Red + Comfort Blue together | Legacy + new palette conflict      |
| Pure White background (`#FFFFFF`)    | Too stark; use Warm White instead  |

---

## 4. Accessibility (WCAG)

| Foreground    | Background   | Contrast Ratio | WCAG AA (4.5:1) | WCAG AAA (7:1) |
|---------------|--------------|----------------|-----------------|----------------|
| Comfort Blue  | Warm White   | ~7.2:1         | ✅ Pass          | ✅ Pass         |
| Charcoal      | Warm White   | ~13.5:1        | ✅ Pass          | ✅ Pass         |
| White         | Comfort Blue | ~7.2:1         | ✅ Pass          | ✅ Pass         |
| White         | Burnt Verm.  | ~4.6:1         | ✅ Pass          | ❌ Fail         |
| Soft Celadon  | Warm White   | ~2.1:1         | ❌ Fail          | ❌ Fail         |
| Comfort Blue  | Burnt Verm.  | ~2.3:1         | ❌ Fail          | ❌ Fail         |

**Rule:** Never use Soft Celadon for text. Always verify contrast before using Burnt Vermilion for text.

---

## 5. Usage by Medium

### Web / Digital
- Use HEX values or CSS custom properties (see SKILL.md Section 5)
- Use `assets/brand-tokens.json` for design system integration

### Print
- Use CMYK values above
- For spot color printing, use Pantone references (approx — verify with print vendor)

### Presentations (PPTX)
- Use HEX values in PowerPoint color picker
- Title slide: Comfort Blue background
- Content slides: Warm White background

### Video / Motion
- Use RGB values
- Comfort Blue (#1B3A6B) for lower thirds and title cards
- Burnt Vermilion (#C0392B) for accent animations only
