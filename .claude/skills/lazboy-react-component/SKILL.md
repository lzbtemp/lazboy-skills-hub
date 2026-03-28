---
name: lazboy-react-component
description: "Generate production-ready React components following La-Z-Boy frontend standards. Includes TypeScript, Tailwind CSS, accessibility (WCAG 2.1 AA), and component testing patterns. Use when building any React UI for La-Z-Boy applications."
version: "1.0.0"
category: Frontend
tags: [frontend, react, typescript, tailwind]
---

# La-Z-Boy React Component Skill

Generates production-ready React components that follow La-Z-Boy's frontend engineering standards.

**Reference files — load when needed:**
- `references/component-patterns.md` — approved component architecture patterns
- `references/accessibility-checklist.md` — WCAG 2.1 AA compliance checklist

**Scripts — run when needed:**
- `scripts/generate_component.py` — scaffold a new component with tests and stories

---

## 1. Component Architecture

### File Structure
```
components/
  ComponentName/
    ComponentName.tsx        # Main component
    ComponentName.test.tsx   # Unit tests
    ComponentName.stories.tsx # Storybook stories
    index.ts                 # Barrel export
```

### Component Template
```tsx
import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface ComponentNameProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
}

const ComponentName = forwardRef<HTMLDivElement, ComponentNameProps>(
  ({ className, variant = 'primary', size = 'md', children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg transition-all duration-200',
          variant === 'primary' && 'bg-[#1B3A6B] text-white',
          variant === 'secondary' && 'bg-[#FAF8F5] text-[#2C2C2C]',
          size === 'sm' && 'px-3 py-1.5 text-sm',
          size === 'md' && 'px-4 py-2 text-base',
          size === 'lg' && 'px-6 py-3 text-lg',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

ComponentName.displayName = 'ComponentName';
export default ComponentName;
```

## 2. Standards

- **TypeScript**: All components must be fully typed — no `any`
- **Tailwind**: Use La-Z-Boy brand tokens (see lazboy-brand skill)
- **Accessibility**: Every interactive element needs `aria-label`, keyboard navigation, focus styles
- **Testing**: Minimum 80% coverage, test user interactions not implementation details
- **Performance**: Use `React.memo` for expensive renders, `useMemo`/`useCallback` where measured

## 3. State Management

- Local state: `useState` / `useReducer`
- Server state: TanStack Query (React Query)
- Global state: Zustand (preferred) or Context API for simple cases
- Never store derived data in state

## 4. Styling Rules

- Use Tailwind CSS utility classes, avoid inline styles
- Brand colors: `#1B3A6B` (primary), `#C0392B` (accent), `#8FAF8A` (green), `#FAF8F5` (bg)
- Responsive: mobile-first (`sm:`, `md:`, `lg:` breakpoints)
- Dark mode: not required for internal tools
- Animations: use `transition-all duration-200` for micro-interactions

## 5. Anti-Patterns

- No `// @ts-ignore` or `as any`
- No inline event handlers in JSX (extract to named functions)
- No `useEffect` for derived state — compute during render
- No barrel exports from large directories (causes bundle bloat)
