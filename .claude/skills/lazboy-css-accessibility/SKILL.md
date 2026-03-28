---
name: lazboy-css-accessibility
description: "Ensure all La-Z-Boy web applications meet WCAG 2.1 AA accessibility standards. Covers semantic HTML, ARIA attributes, keyboard navigation, color contrast, screen reader support, and responsive design. Use when building or reviewing any frontend code."
version: "1.0.0"
category: Frontend
tags: [frontend, accessibility, css, wcag]
---

# La-Z-Boy CSS & Accessibility Skill

Ensures all La-Z-Boy web properties meet WCAG 2.1 AA accessibility standards and follow CSS best practices.

**Reference files — load when needed:**
- `references/wcag-checklist.md` — full WCAG 2.1 AA compliance checklist
- `references/color-contrast.md` — brand color contrast ratios

**Scripts — run when needed:**
- `scripts/audit_accessibility.py` — run automated a11y audit on HTML files
- `scripts/check_contrast.py` — verify color contrast ratios meet WCAG AA

---

## 1. Semantic HTML

Always use semantic elements over generic `div`/`span`:

| Instead of | Use |
|---|---|
| `<div onclick>` | `<button>` |
| `<div class="nav">` | `<nav>` |
| `<div class="header">` | `<header>` |
| `<div class="main">` | `<main>` |
| `<div class="list">` | `<ul>` / `<ol>` |

## 2. Color Contrast Requirements

La-Z-Boy brand colors and their contrast ratios:

| Combination | Ratio | Status |
|---|---|---|
| `#1B3A6B` on `#FFFFFF` | 9.5:1 | AA Pass |
| `#C0392B` on `#FFFFFF` | 5.2:1 | AA Pass |
| `#2C2C2C` on `#FAF8F5` | 12.8:1 | AAA Pass |
| `#8FAF8A` on `#FFFFFF` | 2.8:1 | AA Fail — use on large text only |

## 3. Keyboard Navigation

Every interactive element must be:
- Focusable via `Tab` key
- Activatable via `Enter` or `Space`
- Visually indicated with focus ring: `focus:ring-2 focus:ring-[#1B3A6B] focus:ring-offset-2`
- Escapable (modals, dropdowns) via `Escape` key

```css
/* Standard focus style */
:focus-visible {
  outline: 2px solid #1B3A6B;
  outline-offset: 2px;
}
```

## 4. ARIA Patterns

### Buttons with icons only
```html
<button aria-label="Close dialog">
  <svg>...</svg>
</button>
```

### Loading states
```html
<div aria-live="polite" aria-busy="true">
  Loading skills...
</div>
```

### Form validation
```html
<input aria-invalid="true" aria-describedby="error-msg" />
<span id="error-msg" role="alert">Email is required</span>
```

## 5. Responsive Design

- Mobile-first: start with mobile styles, add breakpoints up
- Touch targets: minimum 44x44px for interactive elements
- Font sizes: minimum 16px body text, never below 12px
- Line height: minimum 1.5 for body text

## 6. Testing Checklist

- [ ] All images have descriptive `alt` text
- [ ] Page has exactly one `<h1>`
- [ ] Heading hierarchy is sequential (h1 → h2 → h3)
- [ ] All forms have associated labels
- [ ] Color is not the only means of conveying information
- [ ] Page is navigable with keyboard only
- [ ] Screen reader announces dynamic content changes
