---
name: lazboy-design-system
description: "Build and maintain the La-Z-Boy design system with reusable UI components, design tokens, and pattern library. Covers component API design, Figma-to-code workflow, theming, and documentation. Use when creating shared UI components or updating the design system."
version: "1.0.0"
category: Designer
tags: [designer, design-system, ui, figma, tokens]
---

# La-Z-Boy Design System Skill

Standards for building and maintaining the La-Z-Boy design system.

**Reference files — load when needed:**
- `references/component-api.md` — component API design guidelines
- `references/token-spec.md` — design token specification

**Scripts — run when needed:**
- `scripts/sync_tokens.py` — sync design tokens from Figma to code
- `scripts/generate_docs.py` — generate component documentation

---

## 1. Design Tokens

### Colors
```json
{
  "color": {
    "primary": { "value": "#1B3A6B", "type": "color" },
    "accent": { "value": "#C0392B", "type": "color" },
    "green": { "value": "#8FAF8A", "type": "color" },
    "background": { "value": "#FAF8F5", "type": "color" },
    "text": { "value": "#2C2C2C", "type": "color" },
    "white": { "value": "#FFFFFF", "type": "color" }
  }
}
```

### Spacing Scale
```
4px  → spacing-1
8px  → spacing-2
12px → spacing-3
16px → spacing-4
24px → spacing-6
32px → spacing-8
48px → spacing-12
64px → spacing-16
```

### Typography Scale
```
text-xs:  12px / 16px
text-sm:  14px / 20px
text-base: 16px / 24px
text-lg:  18px / 28px
text-xl:  20px / 28px
text-2xl: 24px / 32px
text-3xl: 30px / 36px
```

## 2. Component Categories

| Category | Examples |
|---|---|
| **Primitives** | Button, Input, Badge, Avatar |
| **Composites** | Card, Modal, Dropdown, Tabs |
| **Layout** | Container, Grid, Stack, Sidebar |
| **Navigation** | Navbar, Breadcrumb, Pagination |
| **Feedback** | Toast, Alert, Spinner, Progress |
| **Data** | Table, Chart, Stat Card |

## 3. Component API Design Rules

- Props should use semantic names: `variant` not `type`
- Support `className` for custom styling (escape hatch)
- Use `forwardRef` for all components
- Default values should be the most common use case
- Boolean props: `isDisabled` not `disabled` (clearer intent)

### Example Component API
```tsx
<Button
  variant="primary"     // "primary" | "secondary" | "ghost"
  size="md"             // "sm" | "md" | "lg"
  isDisabled={false}
  isLoading={false}
  leftIcon={<PlusIcon />}
  onClick={handleClick}
>
  Add Skill
</Button>
```

## 4. Figma-to-Code Workflow

1. Designer creates component in Figma with auto-layout
2. Developer reviews Figma spec and token usage
3. Code component using design tokens (not hardcoded values)
4. Create Storybook story with all variants
5. Designer reviews implementation in Storybook
6. Component added to design system package

## 5. Documentation Requirements

Every component needs:
- **Usage example** — basic and advanced code snippets
- **Props table** — all props with types, defaults, descriptions
- **Variants** — visual examples of each variant
- **Do / Don't** — correct and incorrect usage examples
- **Accessibility** — keyboard navigation and screen reader behavior
