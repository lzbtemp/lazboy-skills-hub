# Design Token Specification

## Token Taxonomy

Design tokens are organized into the following categories:

| Category | Purpose | Examples |
|----------|---------|---------|
| **color** | All color values | Backgrounds, text, borders, brand |
| **spacing** | Whitespace & layout | Padding, margin, gap |
| **typography** | Text styling | Font families, sizes, weights, line-heights |
| **elevation** | Depth & shadow | Box shadows, z-index layers |
| **motion** | Animation & transition | Duration, easing, delay |
| **border-radius** | Corner rounding | Border radii from sharp to pill |
| **border-width** | Stroke widths | Thin, default, thick borders |
| **opacity** | Transparency levels | Disabled states, overlays |
| **breakpoint** | Responsive thresholds | Mobile, tablet, desktop widths |

---

## Naming Convention

Tokens follow a structured naming pattern:

```
{category}-{property}-{variant}-{state}
```

### Rules

1. **category**: Top-level group (`color`, `spacing`, `font`, `shadow`, `radius`, `motion`)
2. **property**: Specific attribute (`bg`, `text`, `border`, `size`, `weight`, `family`)
3. **variant**: Semantic name or scale value (`primary`, `muted`, `100`, `lg`)
4. **state**: Interactive state, if applicable (`hover`, `active`, `focus`, `disabled`)

### Examples

```
color-bg-primary              → primary background
color-bg-primary-hover        → primary background on hover
color-text-muted              → muted text color
color-border-error            → error border color
spacing-4                     → 16px (4 * 4px base)
font-size-lg                  → large font size
font-weight-semibold          → 600 weight
shadow-md                     → medium elevation shadow
radius-lg                     → large border radius
motion-duration-fast          → short animation duration
motion-easing-ease-out        → ease-out curve
```

---

## Token Tiers

Tokens are organized into three tiers that build on each other:

### Tier 1: Global Tokens (Primitives)

Raw values with no semantic meaning. These are the source of truth.

```json
{
  "color": {
    "blue": {
      "50":  { "value": "#eff6ff" },
      "100": { "value": "#dbeafe" },
      "200": { "value": "#bfdbfe" },
      "300": { "value": "#93c5fd" },
      "400": { "value": "#60a5fa" },
      "500": { "value": "#3b82f6" },
      "600": { "value": "#2563eb" },
      "700": { "value": "#1d4ed8" },
      "800": { "value": "#1e40af" },
      "900": { "value": "#1e3a8a" },
      "950": { "value": "#172554" }
    },
    "neutral": {
      "0":   { "value": "#ffffff" },
      "50":  { "value": "#fafafa" },
      "100": { "value": "#f5f5f5" },
      "200": { "value": "#e5e5e5" },
      "300": { "value": "#d4d4d4" },
      "400": { "value": "#a3a3a3" },
      "500": { "value": "#737373" },
      "600": { "value": "#525252" },
      "700": { "value": "#404040" },
      "800": { "value": "#262626" },
      "900": { "value": "#171717" },
      "950": { "value": "#0a0a0a" }
    }
  },
  "spacing": {
    "0":    { "value": "0px" },
    "0.5":  { "value": "2px" },
    "1":    { "value": "4px" },
    "1.5":  { "value": "6px" },
    "2":    { "value": "8px" },
    "3":    { "value": "12px" },
    "4":    { "value": "16px" },
    "5":    { "value": "20px" },
    "6":    { "value": "24px" },
    "8":    { "value": "32px" },
    "10":   { "value": "40px" },
    "12":   { "value": "48px" },
    "16":   { "value": "64px" },
    "20":   { "value": "80px" },
    "24":   { "value": "96px" }
  },
  "font": {
    "family": {
      "sans":  { "value": "'Inter', ui-sans-serif, system-ui, sans-serif" },
      "mono":  { "value": "'JetBrains Mono', ui-monospace, monospace" }
    },
    "size": {
      "xs":   { "value": "0.75rem" },
      "sm":   { "value": "0.875rem" },
      "md":   { "value": "1rem" },
      "lg":   { "value": "1.125rem" },
      "xl":   { "value": "1.25rem" },
      "2xl":  { "value": "1.5rem" },
      "3xl":  { "value": "1.875rem" },
      "4xl":  { "value": "2.25rem" }
    },
    "weight": {
      "regular":  { "value": "400" },
      "medium":   { "value": "500" },
      "semibold": { "value": "600" },
      "bold":     { "value": "700" }
    },
    "lineHeight": {
      "tight":  { "value": "1.25" },
      "normal": { "value": "1.5" },
      "loose":  { "value": "1.75" }
    }
  },
  "shadow": {
    "xs":  { "value": "0 1px 2px 0 rgb(0 0 0 / 0.05)" },
    "sm":  { "value": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)" },
    "md":  { "value": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)" },
    "lg":  { "value": "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)" },
    "xl":  { "value": "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)" }
  },
  "radius": {
    "none": { "value": "0px" },
    "sm":   { "value": "4px" },
    "md":   { "value": "6px" },
    "lg":   { "value": "8px" },
    "xl":   { "value": "12px" },
    "2xl":  { "value": "16px" },
    "full": { "value": "9999px" }
  },
  "motion": {
    "duration": {
      "instant": { "value": "0ms" },
      "fast":    { "value": "100ms" },
      "normal":  { "value": "200ms" },
      "slow":    { "value": "300ms" },
      "slower":  { "value": "500ms" }
    },
    "easing": {
      "linear":    { "value": "linear" },
      "ease-in":   { "value": "cubic-bezier(0.4, 0, 1, 1)" },
      "ease-out":  { "value": "cubic-bezier(0, 0, 0.2, 1)" },
      "ease-in-out": { "value": "cubic-bezier(0.4, 0, 0.2, 1)" },
      "spring":    { "value": "cubic-bezier(0.34, 1.56, 0.64, 1)" }
    }
  }
}
```

### Tier 2: Alias Tokens (Semantic)

Map global tokens to semantic purpose. These are what most code references.

```json
{
  "color": {
    "bg": {
      "primary":       { "value": "{color.neutral.0}" },
      "secondary":     { "value": "{color.neutral.50}" },
      "tertiary":      { "value": "{color.neutral.100}" },
      "inverse":       { "value": "{color.neutral.900}" },
      "brand":         { "value": "{color.blue.600}" },
      "brand-hover":   { "value": "{color.blue.700}" },
      "brand-active":  { "value": "{color.blue.800}" },
      "success":       { "value": "{color.green.50}" },
      "warning":       { "value": "{color.yellow.50}" },
      "danger":        { "value": "{color.red.50}" },
      "overlay":       { "value": "rgb(0 0 0 / 0.5)" }
    },
    "text": {
      "primary":   { "value": "{color.neutral.900}" },
      "secondary": { "value": "{color.neutral.600}" },
      "muted":     { "value": "{color.neutral.400}" },
      "inverse":   { "value": "{color.neutral.0}" },
      "brand":     { "value": "{color.blue.600}" },
      "success":   { "value": "{color.green.700}" },
      "warning":   { "value": "{color.yellow.700}" },
      "danger":    { "value": "{color.red.700}" },
      "link":      { "value": "{color.blue.600}" },
      "link-hover": { "value": "{color.blue.700}" }
    },
    "border": {
      "default":  { "value": "{color.neutral.200}" },
      "strong":   { "value": "{color.neutral.300}" },
      "focus":    { "value": "{color.blue.500}" },
      "error":    { "value": "{color.red.500}" }
    }
  },
  "spacing": {
    "page-x":      { "value": "{spacing.6}" },
    "page-y":      { "value": "{spacing.8}" },
    "section-gap": { "value": "{spacing.10}" },
    "card-padding": { "value": "{spacing.5}" },
    "input-x":     { "value": "{spacing.3}" },
    "input-y":     { "value": "{spacing.2}" },
    "stack-gap":   { "value": "{spacing.4}" },
    "inline-gap":  { "value": "{spacing.2}" }
  }
}
```

### Tier 3: Component Tokens

Bind alias tokens to specific component properties. Enables per-component customization.

```json
{
  "button": {
    "bg":            { "value": "{color.bg.brand}" },
    "bg-hover":      { "value": "{color.bg.brand-hover}" },
    "bg-active":     { "value": "{color.bg.brand-active}" },
    "text":          { "value": "{color.text.inverse}" },
    "border-radius": { "value": "{radius.md}" },
    "padding-x":     { "value": "{spacing.4}" },
    "padding-y":     { "value": "{spacing.2}" },
    "font-size":     { "value": "{font.size.md}" },
    "font-weight":   { "value": "{font.weight.semibold}" },
    "focus-ring":    { "value": "0 0 0 3px {color.blue.300}" }
  },
  "input": {
    "bg":            { "value": "{color.bg.primary}" },
    "border":        { "value": "{color.border.default}" },
    "border-focus":  { "value": "{color.border.focus}" },
    "border-error":  { "value": "{color.border.error}" },
    "text":          { "value": "{color.text.primary}" },
    "placeholder":   { "value": "{color.text.muted}" },
    "border-radius": { "value": "{radius.md}" },
    "padding-x":     { "value": "{spacing.input-x}" },
    "padding-y":     { "value": "{spacing.input-y}" },
    "font-size":     { "value": "{font.size.md}" }
  }
}
```

---

## CSS Custom Properties

Generated token output uses the `--ds-` prefix to avoid conflicts.

```css
:root {
  /* Global - Colors */
  --ds-color-blue-50: #eff6ff;
  --ds-color-blue-500: #3b82f6;
  --ds-color-blue-600: #2563eb;
  --ds-color-blue-700: #1d4ed8;
  --ds-color-neutral-0: #ffffff;
  --ds-color-neutral-900: #171717;

  /* Global - Spacing */
  --ds-spacing-1: 4px;
  --ds-spacing-2: 8px;
  --ds-spacing-3: 12px;
  --ds-spacing-4: 16px;

  /* Global - Typography */
  --ds-font-family-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
  --ds-font-size-md: 1rem;
  --ds-font-weight-semibold: 600;

  /* Global - Elevation */
  --ds-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);

  /* Global - Radius */
  --ds-radius-md: 6px;

  /* Global - Motion */
  --ds-motion-duration-normal: 200ms;
  --ds-motion-easing-ease-out: cubic-bezier(0, 0, 0.2, 1);

  /* Semantic - Background */
  --ds-color-bg-primary: var(--ds-color-neutral-0);
  --ds-color-bg-brand: var(--ds-color-blue-600);
  --ds-color-bg-brand-hover: var(--ds-color-blue-700);

  /* Semantic - Text */
  --ds-color-text-primary: var(--ds-color-neutral-900);
  --ds-color-text-secondary: var(--ds-color-neutral-600);
  --ds-color-text-inverse: var(--ds-color-neutral-0);

  /* Semantic - Border */
  --ds-color-border-default: var(--ds-color-neutral-200);
  --ds-color-border-focus: var(--ds-color-blue-500);

  /* Component - Button */
  --ds-button-bg: var(--ds-color-bg-brand);
  --ds-button-bg-hover: var(--ds-color-bg-brand-hover);
  --ds-button-text: var(--ds-color-text-inverse);
  --ds-button-border-radius: var(--ds-radius-md);
  --ds-button-padding-x: var(--ds-spacing-4);
  --ds-button-padding-y: var(--ds-spacing-2);

  /* Component - Input */
  --ds-input-bg: var(--ds-color-bg-primary);
  --ds-input-border: var(--ds-color-border-default);
  --ds-input-border-focus: var(--ds-color-border-focus);
  --ds-input-border-radius: var(--ds-radius-md);
}
```

---

## Dark Mode Token Mapping

Dark mode is implemented by remapping alias tokens to different global primitives. Global tokens themselves never change.

```css
[data-theme="dark"],
.dark {
  /* Semantic - Background (remapped) */
  --ds-color-bg-primary: var(--ds-color-neutral-900);
  --ds-color-bg-secondary: var(--ds-color-neutral-800);
  --ds-color-bg-tertiary: var(--ds-color-neutral-700);
  --ds-color-bg-inverse: var(--ds-color-neutral-0);
  --ds-color-bg-brand: var(--ds-color-blue-500);
  --ds-color-bg-brand-hover: var(--ds-color-blue-400);
  --ds-color-bg-brand-active: var(--ds-color-blue-300);
  --ds-color-bg-success: #052e16;
  --ds-color-bg-warning: #422006;
  --ds-color-bg-danger: #450a0a;
  --ds-color-bg-overlay: rgb(0 0 0 / 0.7);

  /* Semantic - Text (remapped) */
  --ds-color-text-primary: var(--ds-color-neutral-50);
  --ds-color-text-secondary: var(--ds-color-neutral-300);
  --ds-color-text-muted: var(--ds-color-neutral-500);
  --ds-color-text-inverse: var(--ds-color-neutral-900);
  --ds-color-text-brand: var(--ds-color-blue-400);
  --ds-color-text-link: var(--ds-color-blue-400);
  --ds-color-text-link-hover: var(--ds-color-blue-300);

  /* Semantic - Border (remapped) */
  --ds-color-border-default: var(--ds-color-neutral-700);
  --ds-color-border-strong: var(--ds-color-neutral-600);
  --ds-color-border-focus: var(--ds-color-blue-400);

  /* Elevation - darker, more visible in dark mode */
  --ds-shadow-xs: 0 1px 2px 0 rgb(0 0 0 / 0.3);
  --ds-shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.4);
  --ds-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.4);
  --ds-shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.4), 0 4px 6px -4px rgb(0 0 0 / 0.4);
}
```

### Strategy

| Layer | Light Mode | Dark Mode |
|-------|-----------|-----------|
| Global tokens | Static | Static (never change) |
| Alias tokens | Point to light globals | Remapped to dark globals |
| Component tokens | Reference aliases | Automatically inherit |

This means component code never needs to know about dark mode. It references component tokens, which reference alias tokens, which are remapped per theme.

---

## Tailwind CSS Integration

### Custom Tailwind Config

```js
// tailwind.config.js
const tokens = require('./tokens/generated/tailwind-tokens');

module.exports = {
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    colors: {
      ...tokens.colors,
      // Map semantic tokens to Tailwind utilities
      bg: {
        primary:   'var(--ds-color-bg-primary)',
        secondary: 'var(--ds-color-bg-secondary)',
        brand:     'var(--ds-color-bg-brand)',
      },
      text: {
        primary:   'var(--ds-color-text-primary)',
        secondary: 'var(--ds-color-text-secondary)',
        muted:     'var(--ds-color-text-muted)',
      },
    },
    spacing: tokens.spacing,
    fontFamily: tokens.fontFamily,
    fontSize: tokens.fontSize,
    fontWeight: tokens.fontWeight,
    lineHeight: tokens.lineHeight,
    borderRadius: tokens.borderRadius,
    boxShadow: tokens.boxShadow,
    transitionDuration: tokens.transitionDuration,
    transitionTimingFunction: tokens.transitionTimingFunction,
    extend: {},
  },
  plugins: [],
};
```

### Usage in Components

```html
<!-- Semantic token classes generated from alias tokens -->
<button class="bg-brand text-inverse px-4 py-2 rounded-md shadow-sm
               hover:bg-brand-hover active:bg-brand-active
               transition-colors duration-normal ease-out">
  Save
</button>
```

---

## Token File Structure

```
tokens/
  source/
    global/
      color.json
      spacing.json
      typography.json
      elevation.json
      motion.json
      radius.json
    semantic/
      light.json
      dark.json
    component/
      button.json
      input.json
      card.json
      modal.json
  generated/           ← output from sync_tokens.py
    css/
      tokens.css
      tokens-dark.css
    tailwind/
      tailwind-tokens.js
    ts/
      tokens.ts
```

---

## Token Governance

1. **Global tokens** are added only when a new primitive color/scale is introduced.
2. **Alias tokens** are added when a new semantic concept emerges (e.g., a new status color).
3. **Component tokens** are added per component; they always reference alias tokens, never globals directly.
4. Breaking changes to tokens require a major version bump.
5. Deprecated tokens are kept for one major version with a `@deprecated` annotation.
