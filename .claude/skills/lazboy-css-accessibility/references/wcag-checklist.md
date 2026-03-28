# WCAG 2.1 AA Compliance Checklist

A practical checklist for web accessibility compliance organized by the four WCAG principles. Each item includes specific CSS/HTML implementation guidance.

---

## 1. Perceivable

Information and UI components must be presentable in ways users can perceive.

### 1.1 Text Alternatives (SC 1.1.1)

- [ ] All `<img>` elements have meaningful `alt` attributes
- [ ] Decorative images use `alt=""` or `role="presentation"`
- [ ] Complex images (charts, infographics) have extended descriptions via `aria-describedby`
- [ ] `<svg>` elements include `<title>` and/or `aria-label`
- [ ] Icon fonts have `aria-hidden="true"` with adjacent screen-reader text
- [ ] `<input type="image">` elements have descriptive `alt` text
- [ ] CSS background images that convey meaning have text alternatives in the DOM

```html
<!-- Informative image -->
<img src="product.jpg" alt="La-Z-Boy Greyson recliner in charcoal fabric">

<!-- Decorative image -->
<img src="divider.png" alt="" role="presentation">

<!-- SVG with accessible name -->
<svg role="img" aria-label="Shopping cart with 3 items">
  <title>Shopping cart with 3 items</title>
  <!-- paths -->
</svg>

<!-- Icon with screen reader text -->
<button>
  <i class="icon-search" aria-hidden="true"></i>
  <span class="sr-only">Search</span>
</button>
```

### 1.2 Time-Based Media (SC 1.2.1 - 1.2.5)

- [ ] Pre-recorded video has captions
- [ ] Pre-recorded audio has transcripts
- [ ] Live video has captions
- [ ] Pre-recorded video has audio descriptions

### 1.3 Adaptable (SC 1.3.1 - 1.3.5)

- [ ] Use semantic HTML elements (`<nav>`, `<main>`, `<article>`, `<section>`, `<aside>`, `<header>`, `<footer>`)
- [ ] Headings follow a logical hierarchy (`h1` > `h2` > `h3`, no skipped levels)
- [ ] Lists use `<ul>`, `<ol>`, or `<dl>` elements
- [ ] Tables use `<th>`, `<caption>`, and `scope` attributes
- [ ] Form inputs are associated with labels via `<label for="...">` or `aria-labelledby`
- [ ] Related form fields are grouped with `<fieldset>` and `<legend>`
- [ ] Reading order matches visual order (avoid CSS `order` that disrupts logical sequence)
- [ ] Content does not rely on sensory characteristics alone ("click the red button")
- [ ] Layout works in both portrait and landscape orientations
- [ ] Autocomplete attributes are used on common input fields

```html
<!-- Semantic structure -->
<header role="banner">
  <nav aria-label="Main navigation">...</nav>
</header>
<main id="main-content">
  <article>
    <h1>Page Title</h1>
    <section aria-labelledby="section-heading">
      <h2 id="section-heading">Section</h2>
    </section>
  </article>
</main>
<footer role="contentinfo">...</footer>

<!-- Table with proper semantics -->
<table>
  <caption>Product Comparison</caption>
  <thead>
    <tr>
      <th scope="col">Feature</th>
      <th scope="col">Basic</th>
      <th scope="col">Premium</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">Recline</th>
      <td>Manual</td>
      <td>Power</td>
    </tr>
  </tbody>
</table>

<!-- Form with proper labeling -->
<form>
  <fieldset>
    <legend>Shipping Address</legend>
    <label for="street">Street Address</label>
    <input id="street" type="text" autocomplete="street-address">
    <label for="city">City</label>
    <input id="city" type="text" autocomplete="address-level2">
  </fieldset>
</form>
```

### 1.4 Distinguishable (SC 1.4.1 - 1.4.13)

- [ ] Color is not the only means of conveying information
- [ ] Text contrast ratio is at least **4.5:1** (normal text) or **3:1** (large text, 18pt / 14pt bold)
- [ ] UI component and graphical object contrast ratio is at least **3:1**
- [ ] Text can be resized up to 200% without loss of content
- [ ] No images of text (except logos)
- [ ] Content reflows at 320px width without horizontal scrolling
- [ ] Line height is at least 1.5x font size; paragraph spacing is at least 2x font size
- [ ] Text spacing can be overridden without breaking functionality
- [ ] Hover/focus content is dismissible, hoverable, and persistent

```css
/* Ensure sufficient text contrast */
body {
  color: #1a1a1a; /* contrast ratio 16.6:1 against white */
  background-color: #ffffff;
}

/* Support text resizing */
html {
  font-size: 100%; /* 16px base */
}
body {
  font-size: 1rem;
  line-height: 1.5;
}
p {
  margin-bottom: 1.5em;
}

/* Reflow support — avoid fixed widths */
.container {
  max-width: 80rem;
  width: 100%;
  padding: 0 1rem;
}

/* Support user text spacing overrides */
* {
  line-height: inherit !important; /* Don't override to fixed values */
}

/* Hover/focus content: dismissible, hoverable, persistent */
.tooltip-trigger:hover + .tooltip,
.tooltip-trigger:focus + .tooltip,
.tooltip:hover {
  display: block;
}
.tooltip-trigger:focus + .tooltip {
  /* Allow Escape to dismiss via JS */
}
```

---

## 2. Operable

UI components and navigation must be operable by all users.

### 2.1 Keyboard Accessible (SC 2.1.1 - 2.1.4)

- [ ] All interactive elements are reachable via Tab key
- [ ] Custom widgets use appropriate ARIA roles with keyboard support
- [ ] No keyboard traps (user can always Tab away)
- [ ] Single-key shortcuts can be remapped or disabled
- [ ] Focus order follows logical reading order
- [ ] Custom elements use `tabindex="0"` for focusability (avoid positive `tabindex`)

```html
<!-- Skip link -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<!-- Custom button that is keyboard accessible -->
<div role="button" tabindex="0"
     aria-pressed="false"
     onkeydown="if(event.key==='Enter'||event.key===' '){activate(this)}">
  Toggle Feature
</div>
```

```css
/* Skip link styling */
.skip-link {
  position: absolute;
  top: -100%;
  left: 0;
  padding: 0.75rem 1.5rem;
  background: #000;
  color: #fff;
  z-index: 10000;
  font-weight: 600;
}
.skip-link:focus {
  top: 0;
}

/* Visible focus indicators */
:focus-visible {
  outline: 3px solid #2563eb;
  outline-offset: 2px;
}

/* Never remove focus outlines globally */
/* BAD: *:focus { outline: none; } */
```

**Keyboard Patterns for Common Widgets:**

| Widget | Keys |
|--------|------|
| Button | Enter, Space |
| Link | Enter |
| Checkbox | Space |
| Radio group | Arrow keys (within group), Tab (between groups) |
| Tab panel | Arrow keys (between tabs), Tab (into panel) |
| Menu | Arrow keys, Enter, Escape |
| Dialog/Modal | Tab (trap focus), Escape (close) |
| Accordion | Enter/Space (toggle), Arrow keys (between headers) |
| Combobox | Arrow keys, Enter, Escape, typing to filter |

### 2.2 Enough Time (SC 2.2.1 - 2.2.2)

- [ ] Users can extend, adjust, or disable time limits
- [ ] Auto-updating content can be paused, stopped, or hidden
- [ ] Session timeouts warn users and allow extension

### 2.3 Seizures and Physical Reactions (SC 2.3.1)

- [ ] No content flashes more than 3 times per second
- [ ] Respect `prefers-reduced-motion`

```css
/* Respect motion preferences */
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
```

### 2.4 Navigable (SC 2.4.1 - 2.4.10)

- [ ] Skip navigation link is present and functional
- [ ] Pages have descriptive `<title>` elements
- [ ] Focus order is logical and predictable
- [ ] Link text is descriptive (no "click here" or "read more" without context)
- [ ] Multiple ways to find pages (navigation, search, site map)
- [ ] Headings and labels are descriptive
- [ ] Focus is visible on all interactive elements

```html
<!-- Descriptive page title -->
<title>Product Details - Greyson Recliner | La-Z-Boy</title>

<!-- Descriptive link text -->
<!-- BAD -->
<a href="/recliners">Click here</a>

<!-- GOOD -->
<a href="/recliners">Browse all recliners</a>

<!-- GOOD — with context for repeated patterns -->
<a href="/product/123" aria-label="View details for Greyson Recliner">
  View details
</a>
```

### 2.5 Input Modalities (SC 2.5.1 - 2.5.4)

- [ ] Pointer gestures have single-pointer alternatives
- [ ] Pointer cancellation: down-event does not trigger action (use click/up events)
- [ ] Accessible names match visible labels
- [ ] Motion-based input has UI alternatives

---

## 3. Understandable

Information and UI operation must be understandable.

### 3.1 Readable (SC 3.1.1 - 3.1.2)

- [ ] Page language is declared with `<html lang="en">`
- [ ] Language changes within the page use the `lang` attribute

```html
<html lang="en">
<body>
  <p>Welcome to our store.</p>
  <p lang="es">Bienvenidos a nuestra tienda.</p>
</body>
</html>
```

### 3.2 Predictable (SC 3.2.1 - 3.2.4)

- [ ] Focus changes do not cause unexpected context changes
- [ ] Input changes do not cause unexpected context changes
- [ ] Navigation is consistent across pages
- [ ] Components with same function are identified consistently

### 3.3 Input Assistance (SC 3.3.1 - 3.3.4)

- [ ] Input errors are identified and described in text
- [ ] Form fields have visible labels and instructions
- [ ] Error suggestions are provided when possible
- [ ] Important submissions can be reviewed, confirmed, or reversed

```html
<!-- Error messaging -->
<label for="email">Email Address</label>
<input id="email" type="email"
       aria-required="true"
       aria-invalid="true"
       aria-describedby="email-error">
<p id="email-error" role="alert" class="error-message">
  Please enter a valid email address (e.g., name@example.com).
</p>
```

```css
/* Error state styling — not relying on color alone */
.error-message {
  color: #b91c1c;
  font-weight: 600;
}
.error-message::before {
  content: "\26A0\FE0F "; /* warning icon as additional indicator */
}
input[aria-invalid="true"] {
  border: 2px solid #b91c1c;
  box-shadow: 0 0 0 1px #b91c1c;
}
```

---

## 4. Robust

Content must be robust enough for a wide variety of user agents, including assistive technologies.

### 4.1 Compatible (SC 4.1.1 - 4.1.3)

- [ ] HTML validates without significant parsing errors
- [ ] All interactive elements have accessible names
- [ ] Status messages use appropriate ARIA live regions

```html
<!-- Live region for dynamic status updates -->
<div aria-live="polite" aria-atomic="true" class="sr-only">
  3 items added to your cart.
</div>

<!-- Assertive for urgent messages -->
<div role="alert" aria-live="assertive">
  Your session will expire in 2 minutes.
</div>

<!-- Custom component with full ARIA -->
<div role="combobox"
     aria-expanded="false"
     aria-haspopup="listbox"
     aria-labelledby="combo-label"
     aria-owns="combo-listbox">
  <label id="combo-label">Choose a fabric</label>
  <input type="text"
         aria-autocomplete="list"
         aria-controls="combo-listbox">
  <ul id="combo-listbox" role="listbox" hidden>
    <li role="option" id="opt1">Charcoal Microfiber</li>
    <li role="option" id="opt2">Cream Leather</li>
  </ul>
</div>
```

---

## ARIA Roles Quick Reference

### Landmark Roles

| Role | HTML Equivalent | Purpose |
|------|----------------|---------|
| `banner` | `<header>` (top-level) | Site header |
| `navigation` | `<nav>` | Navigation region |
| `main` | `<main>` | Primary content |
| `complementary` | `<aside>` | Supporting content |
| `contentinfo` | `<footer>` (top-level) | Site footer |
| `search` | `<search>` | Search functionality |
| `form` | `<form>` (when labeled) | Form region |
| `region` | `<section>` (when labeled) | Generic labeled region |

### Widget Roles

| Role | Required States/Properties |
|------|---------------------------|
| `button` | `aria-pressed` (toggle), `aria-expanded` (menu) |
| `checkbox` | `aria-checked` |
| `radio` | `aria-checked`, within `radiogroup` |
| `tab` | `aria-selected`, `aria-controls`, within `tablist` |
| `tabpanel` | `aria-labelledby` |
| `dialog` | `aria-labelledby`, `aria-modal` |
| `alertdialog` | `aria-labelledby`, `aria-describedby` |
| `slider` | `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| `progressbar` | `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| `switch` | `aria-checked` |
| `menu` / `menuitem` | `aria-haspopup`, `aria-expanded` |
| `tree` / `treeitem` | `aria-expanded`, `aria-level` |
| `grid` / `gridcell` | `aria-rowindex`, `aria-colindex` |

---

## Focus Management Patterns

### Modal Dialog Focus Trap

```javascript
function trapFocus(dialog) {
  const focusable = dialog.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), ' +
    'select:not([disabled]), textarea:not([disabled]), [tabindex="0"]'
  );
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  dialog.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    if (e.key === 'Escape') {
      closeDialog(dialog);
    }
  });

  first.focus();
}
```

### Restoring Focus After Dynamic Content

```javascript
function openPanel(trigger, panel) {
  // Store the trigger element
  panel.dataset.triggerElement = trigger.id;
  panel.hidden = false;
  panel.querySelector('[tabindex="-1"], a, button').focus();
}

function closePanel(panel) {
  panel.hidden = true;
  // Restore focus to the trigger
  const trigger = document.getElementById(panel.dataset.triggerElement);
  if (trigger) trigger.focus();
}
```

---

## Screen Reader Only Utility

```css
/* Visually hidden but accessible to screen readers */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Allow the element to be focusable when navigated to */
.sr-only-focusable:focus,
.sr-only-focusable:active {
  position: static;
  width: auto;
  height: auto;
  padding: inherit;
  margin: inherit;
  overflow: visible;
  clip: auto;
  white-space: inherit;
}
```

---

## Testing Checklist

### Manual Testing

- [ ] Navigate entire page using only keyboard (Tab, Shift+Tab, Enter, Space, Arrows, Escape)
- [ ] Test with screen reader (VoiceOver on macOS, NVDA/JAWS on Windows)
- [ ] Zoom browser to 200% and verify no content is lost
- [ ] Set browser text size to "very large" in accessibility settings
- [ ] Test with Windows High Contrast Mode
- [ ] Verify all images have appropriate alt text
- [ ] Confirm all form fields have visible labels
- [ ] Check that error messages are announced by screen readers

### Automated Testing Tools

- **axe DevTools** — Browser extension for automated WCAG testing
- **Lighthouse** — Chrome DevTools accessibility audit
- **WAVE** — Web accessibility evaluation tool
- **pa11y** — CLI accessibility testing
- **eslint-plugin-jsx-a11y** — ESLint rules for JSX accessibility
- **@axe-core/react** — Runtime accessibility checks in React dev mode

---

*Reference: [WCAG 2.1 Specification](https://www.w3.org/TR/WCAG21/) | [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/) | [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)*
