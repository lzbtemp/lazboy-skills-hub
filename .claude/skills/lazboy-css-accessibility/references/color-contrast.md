# Color Contrast Reference

A comprehensive guide to color contrast requirements, tools, accessible palettes, and CSS media queries for user preferences.

---

## WCAG Contrast Ratios

### Minimum Requirements (AA)

| Element Type | Minimum Ratio | Definition |
|-------------|---------------|------------|
| Normal text (< 18pt / < 14pt bold) | **4.5:1** | Body text, labels, captions |
| Large text (>= 18pt / >= 14pt bold) | **3:1** | Headings, prominent text |
| UI components & graphical objects | **3:1** | Buttons, form borders, icons, focus indicators |

### Enhanced Requirements (AAA)

| Element Type | Minimum Ratio | Notes |
|-------------|---------------|-------|
| Normal text | **7:1** | Recommended for body text when possible |
| Large text | **4.5:1** | Recommended for headings |

### What Counts as "Large Text"

- **18pt (24px)** regular weight or larger
- **14pt (18.66px) bold** (700+ weight) or larger
- These thresholds assume default browser zoom at 1x

---

## Calculating Contrast Ratio

### Relative Luminance Formula

Relative luminance (L) is calculated from linearized sRGB values:

```
L = 0.2126 * R_lin + 0.7152 * G_lin + 0.0722 * B_lin
```

Where each channel is linearized:
```
if sRGB_channel <= 0.04045:
    linear = sRGB_channel / 12.92
else:
    linear = ((sRGB_channel + 0.055) / 1.055) ^ 2.4
```

### Contrast Ratio Formula

```
ratio = (L_lighter + 0.05) / (L_darker + 0.05)
```

Where `L_lighter` is the relative luminance of the lighter color and `L_darker` is the darker.

---

## Common Failing Color Combinations

These frequently used combinations **fail** WCAG AA for normal text:

| Foreground | Background | Ratio | Status |
|-----------|-----------|-------|--------|
| `#999999` (gray) | `#ffffff` (white) | 2.85:1 | FAIL |
| `#ff0000` (red) | `#ffffff` (white) | 4.00:1 | FAIL |
| `#00ff00` (green) | `#ffffff` (white) | 1.37:1 | FAIL |
| `#0000ff` (blue) | `#000000` (black) | 2.44:1 | FAIL |
| `#ff6600` (orange) | `#ffffff` (white) | 3.00:1 | FAIL |
| `#ffff00` (yellow) | `#ffffff` (white) | 1.07:1 | FAIL |
| `#66ccff` (light blue) | `#ffffff` (white) | 1.98:1 | FAIL |
| `#cccccc` (light gray) | `#ffffff` (white) | 1.60:1 | FAIL |
| `#777777` (gray) | `#444444` (dark gray) | 2.15:1 | FAIL |
| `#ffffff` (white) | `#66bb6a` (green) | 2.31:1 | FAIL |

### Common Offenders in UI Design

- **Placeholder text**: Default `#a9a9a9` on white = 2.32:1 (FAIL). Use `#767676` or darker.
- **Disabled states**: Often too low contrast. Ensure at least 3:1 for discoverability or use other cues (icons, text patterns).
- **Links vs body text**: Links must be distinguishable from surrounding text by more than color alone (underline, bold, or 3:1 contrast between link and body text).
- **Subtle borders**: Light gray borders on white backgrounds often fail the 3:1 UI component ratio.

---

## Accessible Color Palettes

### Neutral Palette (passes AA on white `#ffffff`)

| Swatch | Hex | Ratio vs White | Use |
|--------|-----|---------------|-----|
| Black | `#000000` | 21.0:1 | Primary text |
| Dark Gray | `#1a1a1a` | 16.6:1 | Primary text |
| Body Gray | `#333333` | 12.6:1 | Body text |
| Medium Gray | `#555555` | 7.46:1 | Secondary text |
| Accessible Gray | `#767676` | 4.54:1 | Minimum for small text |
| UI Border Gray | `#949494` | 3.03:1 | UI components only |

### Accessible Brand Colors (passes 4.5:1 on white)

| Color | Hex | Ratio vs White | Notes |
|-------|-----|---------------|-------|
| Accessible Blue | `#0055b8` | 7.01:1 | Links, primary actions |
| Accessible Green | `#007a33` | 5.27:1 | Success states |
| Accessible Red | `#b91c1c` | 6.27:1 | Error states |
| Accessible Orange | `#a35200` | 5.04:1 | Warnings |
| Accessible Purple | `#6b21a8` | 7.47:1 | Accents |

### Dark Mode Palette (passes AA on dark `#1a1a1a`)

| Swatch | Hex | Ratio vs `#1a1a1a` | Use |
|--------|-----|-------------------|-----|
| White | `#ffffff` | 16.6:1 | Primary text |
| Light | `#e5e5e5` | 13.3:1 | Primary text |
| Secondary | `#a3a3a3` | 6.63:1 | Secondary text |
| Muted | `#737373` | 3.67:1 | Muted / large text only |
| Light Blue | `#60a5fa` | 5.28:1 | Links |
| Light Green | `#4ade80` | 7.50:1 | Success |
| Light Red | `#f87171` | 4.85:1 | Errors |

---

## Dark Mode Considerations

### Contrast in Dark Themes

- **Avoid pure white on pure black**: `#ffffff` on `#000000` (21:1) causes halation and eye strain. Use off-white (`#e5e5e5`) on dark gray (`#1a1a1a` to `#121212`).
- **Elevated surfaces should be lighter**: Use subtle background shifts (`#1e1e1e`, `#252525`, `#2d2d2d`) for layering rather than shadows alone.
- **Saturated colors vibrate on dark backgrounds**: Desaturate brand colors or use lighter tints for dark mode.
- **Re-test all contrast ratios**: Colors that pass on white may fail on dark backgrounds and vice versa.

### Implementation Pattern

```css
:root {
  /* Light mode (default) */
  --color-text-primary: #1a1a1a;
  --color-text-secondary: #555555;
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f5f5f5;
  --color-border: #949494;
  --color-link: #0055b8;
  --color-error: #b91c1c;
  --color-success: #007a33;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-text-primary: #e5e5e5;
    --color-text-secondary: #a3a3a3;
    --color-bg-primary: #1a1a1a;
    --color-bg-secondary: #252525;
    --color-border: #525252;
    --color-link: #60a5fa;
    --color-error: #f87171;
    --color-success: #4ade80;
  }
}
```

---

## CSS Media Queries for User Preferences

### `prefers-color-scheme`

Detects whether the user prefers a light or dark color theme.

```css
/* Light mode (default) */
body {
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  body {
    background: #1a1a1a;
    color: #e5e5e5;
  }
}
```

```javascript
// JavaScript detection
const darkMode = window.matchMedia('(prefers-color-scheme: dark)');
darkMode.addEventListener('change', (e) => {
  document.body.classList.toggle('dark-mode', e.matches);
});
```

### `prefers-reduced-motion`

Detects whether the user has requested reduced motion.

```css
/* Default animations */
.fade-in {
  animation: fadeIn 0.3s ease-in-out;
}

.slide-up {
  transition: transform 0.3s ease;
}

/* Remove or reduce animations for users who prefer reduced motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* Alternative: provide simpler animations instead of removing them entirely */
@media (prefers-reduced-motion: reduce) {
  .fade-in {
    animation: none;
    opacity: 1;
  }

  .slide-up {
    transition: opacity 0.1s ease;
  }
}
```

### `prefers-contrast`

Detects whether the user has requested increased or decreased contrast.

```css
/* High contrast mode */
@media (prefers-contrast: more) {
  :root {
    --color-text-primary: #000000;
    --color-bg-primary: #ffffff;
    --color-border: #000000;
  }

  /* Ensure all borders are visible */
  button, input, select, textarea {
    border: 2px solid #000000;
  }

  /* Make focus indicators extra visible */
  :focus-visible {
    outline: 3px solid #000000;
    outline-offset: 3px;
  }
}

/* Low contrast / less aggressive styling */
@media (prefers-contrast: less) {
  :root {
    --color-text-primary: #333333;
    --color-bg-primary: #f0f0f0;
  }
}
```

### `forced-colors` (Windows High Contrast)

Detects when the browser is in forced colors mode (e.g., Windows High Contrast).

```css
@media (forced-colors: active) {
  /* System colors are enforced. Use these keywords: */
  .custom-button {
    border: 2px solid ButtonText;
    background: ButtonFace;
    color: ButtonText;
  }

  .custom-button:hover {
    border-color: Highlight;
    color: Highlight;
  }

  /* Ensure custom checkboxes/radios remain visible */
  .custom-checkbox::before {
    forced-color-adjust: none; /* opt out only when providing proper alternatives */
  }

  /* Icons that rely on color need borders */
  .status-icon {
    border: 1px solid currentColor;
  }
}
```

### `prefers-reduced-transparency`

Detects whether the user prefers reduced transparency.

```css
@media (prefers-reduced-transparency: reduce) {
  .modal-overlay {
    background: #000000; /* Solid instead of semi-transparent */
  }

  .glass-effect {
    backdrop-filter: none;
    background: var(--color-bg-secondary);
  }
}
```

---

## Contrast Checking Tools

### Browser Extensions & DevTools

| Tool | Type | Features |
|------|------|----------|
| **Chrome DevTools** | Built-in | Inspect element shows contrast ratio in color picker |
| **Firefox Accessibility Inspector** | Built-in | Full contrast checking, tab order visualization |
| **axe DevTools** | Extension | Automated contrast scanning across entire page |
| **WAVE** | Extension | Visual indicators for contrast issues |

### Online Tools

| Tool | URL | Features |
|------|-----|----------|
| **WebAIM Contrast Checker** | webaim.org/resources/contrastchecker | Quick ratio check with AA/AAA results |
| **Coolors Contrast Checker** | coolors.co/contrast-checker | Visual preview with text samples |
| **Adobe Color Accessibility** | color.adobe.com/create/color-accessibility | Full palette contrast analysis |
| **Stark** | getstark.co | Design tool plugin (Figma, Sketch) |
| **Who Can Use** | whocanuse.com | Shows how colors appear with various vision types |

### CLI / CI Tools

| Tool | Install | Usage |
|------|---------|-------|
| **pa11y** | `npm install -g pa11y` | `pa11y https://example.com` |
| **axe-core** | `npm install axe-core` | Automated testing in test suites |
| **lighthouse** | `npm install -g lighthouse` | `lighthouse --only-categories=accessibility` |
| **color-contrast-checker** | `pip install colour-contrast-checker` | Python library for CI pipelines |

---

## Quick Reference: Safe Color Pairs

### On White (`#ffffff`)

```
#1a1a1a  ████  16.6:1  ✓ AA  ✓ AAA  (near-black)
#333333  ████  12.6:1  ✓ AA  ✓ AAA  (body text)
#555555  ████   7.5:1  ✓ AA  ✓ AAA  (secondary)
#767676  ████   4.5:1  ✓ AA  ✗ AAA  (minimum for body)
#0055b8  ████   7.0:1  ✓ AA  ✓ AAA  (link blue)
#b91c1c  ████   6.3:1  ✓ AA  ✗ AAA  (error red)
#007a33  ████   5.3:1  ✓ AA  ✗ AAA  (success green)
```

### On Black (`#1a1a1a`)

```
#ffffff  ████  16.6:1  ✓ AA  ✓ AAA  (white)
#e5e5e5  ████  13.3:1  ✓ AA  ✓ AAA  (light gray)
#a3a3a3  ████   6.6:1  ✓ AA  ✗ AAA  (medium gray)
#60a5fa  ████   5.3:1  ✓ AA  ✗ AAA  (light blue)
#4ade80  ████   7.5:1  ✓ AA  ✓ AAA  (light green)
#f87171  ████   4.9:1  ✓ AA  ✗ AAA  (light red)
```

---

*Reference: [WCAG 2.1 SC 1.4.3](https://www.w3.org/TR/WCAG21/#contrast-minimum) | [WCAG 2.1 SC 1.4.6](https://www.w3.org/TR/WCAG21/#contrast-enhanced) | [WCAG 2.1 SC 1.4.11](https://www.w3.org/TR/WCAG21/#non-text-contrast)*
