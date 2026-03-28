# Accessibility Guide for React Applications

Comprehensive reference for building accessible React applications that conform to
WCAG 2.1 AA standards.

## 1. Semantic HTML

Always start with the correct HTML element before reaching for ARIA attributes.
Native elements carry built-in semantics, keyboard behavior, and screen reader support.

```typescript
// BAD: div soup with ARIA bolted on
<div role="button" tabIndex={0} onClick={handleClick}>Submit</div>

// GOOD: native element
<button onClick={handleClick}>Submit</button>
```

### Common Semantic Elements

| Instead of | Use |
|-----------|-----|
| `<div>` with click handler | `<button>` |
| `<div>` for navigation | `<nav>` |
| `<div>` for page section | `<section>` with heading |
| `<div>` for main content | `<main>` |
| `<div>` for sidebar | `<aside>` |
| `<span>` for link | `<a href="...">` |
| `<div>` for list | `<ul>` / `<ol>` |
| `<div>` for table | `<table>` |
| `<div>` for header | `<header>` |
| `<div>` for footer | `<footer>` |

### Heading Hierarchy

Maintain a logical heading order. Do not skip levels.

```typescript
// GOOD: logical heading hierarchy
function ProductPage() {
  return (
    <main>
      <h1>Product Catalog</h1>
      <section>
        <h2>Featured Products</h2>
        <article>
          <h3>Product Name</h3>
          <p>Description...</p>
        </article>
      </section>
      <section>
        <h2>All Categories</h2>
        <h3>Electronics</h3>
        <h3>Clothing</h3>
      </section>
    </main>
  );
}
```

## 2. ARIA Roles, States, and Properties

Use ARIA only when native HTML is insufficient. The first rule of ARIA: do not
use ARIA if you can use a native HTML element.

### 2.1 Landmark Roles

```typescript
function AppLayout() {
  return (
    <>
      <header role="banner">
        <nav aria-label="Primary navigation">
          <ul>
            <li><a href="/home">Home</a></li>
            <li><a href="/products">Products</a></li>
          </ul>
        </nav>
      </header>
      <main role="main">
        {/* Page content */}
      </main>
      <aside aria-label="Related products">
        {/* Sidebar */}
      </aside>
      <footer role="contentinfo">
        {/* Footer */}
      </footer>
    </>
  );
}
```

### 2.2 Live Regions

Announce dynamic content changes to screen readers.

```typescript
function NotificationArea({ messages }: { messages: string[] }) {
  return (
    <div aria-live="polite" aria-atomic="true" className="sr-only">
      {messages.map((msg, i) => (
        <p key={i}>{msg}</p>
      ))}
    </div>
  );
}

// For urgent alerts
function ErrorAlert({ message }: { message: string }) {
  return (
    <div role="alert" aria-live="assertive">
      <p>{message}</p>
    </div>
  );
}
```

### 2.3 ARIA States for Interactive Components

```typescript
// Expandable section
function Accordion({ title, children }: { title: string; children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const contentId = useId();

  return (
    <div>
      <button
        aria-expanded={isOpen}
        aria-controls={contentId}
        onClick={() => setIsOpen(!isOpen)}
      >
        {title}
      </button>
      <div id={contentId} role="region" hidden={!isOpen}>
        {children}
      </div>
    </div>
  );
}

// Toggle button
function ToggleButton({ label, pressed, onToggle }: {
  label: string;
  pressed: boolean;
  onToggle: () => void;
}) {
  return (
    <button aria-pressed={pressed} onClick={onToggle}>
      {label}
    </button>
  );
}
```

## 3. Keyboard Navigation

All interactive elements must be operable with keyboard alone.

### 3.1 Focus Management Hook

```typescript
function useFocusTrap(ref: RefObject<HTMLElement>) {
  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const focusableSelectors = [
      "a[href]", "button:not([disabled])", "input:not([disabled])",
      "select:not([disabled])", "textarea:not([disabled])",
      "[tabindex]:not([tabindex='-1'])"
    ].join(", ");

    const focusableElements = element.querySelectorAll<HTMLElement>(focusableSelectors);
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== "Tab") return;

      if (e.shiftKey) {
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable?.focus();
        }
      } else {
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable?.focus();
        }
      }
    }

    element.addEventListener("keydown", handleKeyDown);
    firstFocusable?.focus();

    return () => element.removeEventListener("keydown", handleKeyDown);
  }, [ref]);
}
```

### 3.2 Roving Tab Index

For composite widgets (toolbars, tab lists, menus), use roving tabindex so only
one item in the group is tabbable at a time.

```typescript
function useRovingTabIndex(itemCount: number) {
  const [activeIndex, setActiveIndex] = useState(0);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    let newIndex = activeIndex;

    switch (e.key) {
      case "ArrowRight":
      case "ArrowDown":
        e.preventDefault();
        newIndex = (activeIndex + 1) % itemCount;
        break;
      case "ArrowLeft":
      case "ArrowUp":
        e.preventDefault();
        newIndex = (activeIndex - 1 + itemCount) % itemCount;
        break;
      case "Home":
        e.preventDefault();
        newIndex = 0;
        break;
      case "End":
        e.preventDefault();
        newIndex = itemCount - 1;
        break;
    }

    setActiveIndex(newIndex);
  }, [activeIndex, itemCount]);

  const getTabIndex = useCallback(
    (index: number) => (index === activeIndex ? 0 : -1),
    [activeIndex]
  );

  return { activeIndex, handleKeyDown, getTabIndex };
}

// Usage in a toolbar
function Toolbar({ items }: { items: ToolbarItem[] }) {
  const { activeIndex, handleKeyDown, getTabIndex } = useRovingTabIndex(items.length);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    refs.current[activeIndex]?.focus();
  }, [activeIndex]);

  return (
    <div role="toolbar" aria-label="Formatting" onKeyDown={handleKeyDown}>
      {items.map((item, i) => (
        <button
          key={item.id}
          ref={(el) => { refs.current[i] = el; }}
          tabIndex={getTabIndex(i)}
          aria-label={item.label}
        >
          {item.icon}
        </button>
      ))}
    </div>
  );
}
```

### 3.3 Skip Navigation Link

```typescript
function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-white focus:p-2"
    >
      Skip to main content
    </a>
  );
}
```

## 4. Focus Management

### 4.1 Modal Dialog

```typescript
function Modal({ isOpen, onClose, title, children }: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      previousFocus.current = document.activeElement as HTMLElement;
      modalRef.current?.focus();
    } else {
      previousFocus.current?.focus();
    }
  }, [isOpen]);

  useFocusTrap(modalRef);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      <div className="overlay" aria-hidden="true" onClick={onClose} />
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
      >
        <h2 id="modal-title">{title}</h2>
        {children}
        <button onClick={onClose}>Close</button>
      </div>
    </>
  );
}
```

### 4.2 Focus After Route Change

```typescript
function useFocusOnRouteChange() {
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);

  useEffect(() => {
    mainRef.current?.focus();
  }, [location.pathname]);

  return mainRef;
}

function App() {
  const mainRef = useFocusOnRouteChange();
  return <main ref={mainRef} tabIndex={-1}>{/* routes */}</main>;
}
```

## 5. Form Accessibility

### 5.1 Labeled Inputs

Every form control must have an associated label.

```typescript
function FormField({ id, label, error, required, ...inputProps }: {
  id: string;
  label: string;
  error?: string;
  required?: boolean;
} & InputHTMLAttributes<HTMLInputElement>) {
  const errorId = `${id}-error`;
  const descriptionId = `${id}-desc`;

  return (
    <div className="form-field">
      <label htmlFor={id}>
        {label}
        {required && <span aria-hidden="true"> *</span>}
        {required && <span className="sr-only"> (required)</span>}
      </label>
      <input
        id={id}
        aria-required={required}
        aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined}
        {...inputProps}
      />
      {error && (
        <p id={errorId} role="alert" className="error-message">
          {error}
        </p>
      )}
    </div>
  );
}
```

### 5.2 Form Validation Announcements

```typescript
function useFormValidation() {
  const [announcement, setAnnouncement] = useState("");

  const announceErrors = useCallback((errors: Record<string, string>) => {
    const count = Object.keys(errors).length;
    if (count > 0) {
      setAnnouncement(
        `Form has ${count} error${count > 1 ? "s" : ""}. ` +
        Object.values(errors).join(". ")
      );
    }
  }, []);

  const AnnouncerRegion = () => (
    <div aria-live="assertive" aria-atomic="true" className="sr-only">
      {announcement}
    </div>
  );

  return { announceErrors, AnnouncerRegion };
}
```

### 5.3 Fieldset and Legend for Grouped Controls

```typescript
function RadioGroup({ legend, name, options, value, onChange }: {
  legend: string;
  name: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <fieldset>
      <legend>{legend}</legend>
      {options.map((opt) => (
        <label key={opt.value}>
          <input
            type="radio"
            name={name}
            value={opt.value}
            checked={value === opt.value}
            onChange={() => onChange(opt.value)}
          />
          {opt.label}
        </label>
      ))}
    </fieldset>
  );
}
```

## 6. Color Contrast and Visual Accessibility

### 6.1 Minimum Contrast Ratios (WCAG 2.1 AA)

| Element | Minimum Ratio |
|---------|--------------|
| Normal text (< 18px / 14px bold) | 4.5:1 |
| Large text (>= 18px / 14px bold) | 3:1 |
| UI components and graphics | 3:1 |
| Non-text contrast (icons, borders) | 3:1 |

### 6.2 Do Not Rely on Color Alone

```typescript
// BAD: status indicated only by color
<span style={{ color: isValid ? "green" : "red" }}>{value}</span>

// GOOD: color + icon + text
<span className={isValid ? "text-green" : "text-red"}>
  {isValid ? <CheckIcon aria-hidden="true" /> : <XIcon aria-hidden="true" />}
  {isValid ? "Valid" : "Invalid"}
</span>
```

### 6.3 Reduced Motion

```typescript
// CSS
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

// React hook
function usePrefersReducedMotion(): boolean {
  const [prefersReduced, setPrefersReduced] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReduced(mql.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReduced(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return prefersReduced;
}
```

## 7. Screen Reader Testing

### 7.1 Screen Reader Only Utility

```css
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
```

### 7.2 Testing Checklist

1. **VoiceOver (macOS):** Cmd+F5 to toggle. Use Ctrl+Option+arrows to navigate.
2. **NVDA (Windows):** Free screen reader. Tab through interactive elements.
3. **axe-core / axe DevTools:** Automated accessibility audit in browser.
4. **React Testing Library:** Queries by role enforce accessible markup.

```typescript
// Testing Library encourages accessible queries
import { render, screen } from "@testing-library/react";

test("renders accessible form", () => {
  render(<LoginForm />);

  // Query by role -- tests that ARIA/semantics are correct
  expect(screen.getByRole("textbox", { name: /email/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();

  // Query by label text
  expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
});
```

### 7.3 Automated Testing with jest-axe

```typescript
import { axe, toHaveNoViolations } from "jest-axe";
import { render } from "@testing-library/react";

expect.extend(toHaveNoViolations);

test("page has no accessibility violations", async () => {
  const { container } = render(<ProductPage />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

## 8. Common ARIA Patterns Quick Reference

| Widget | Key ARIA Attributes |
|--------|-------------------|
| Dialog/Modal | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` |
| Tab Panel | `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected` |
| Accordion | `aria-expanded`, `aria-controls`, `role="region"` |
| Combobox | `role="combobox"`, `aria-expanded`, `aria-activedescendant` |
| Menu | `role="menu"`, `role="menuitem"`, `aria-haspopup` |
| Alert | `role="alert"`, `aria-live="assertive"` |
| Status | `role="status"`, `aria-live="polite"` |
| Progress | `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| Tooltip | `role="tooltip"`, triggered by `aria-describedby` |
| Breadcrumb | `nav` with `aria-label="Breadcrumb"` |
