# React Component Accessibility Checklist

A practical checklist for building accessible React components, organized by component type and interaction pattern.

---

## Table of Contents

1. [General Principles](#1-general-principles)
2. [Buttons](#2-buttons)
3. [Modals / Dialogs](#3-modals--dialogs)
4. [Tabs](#4-tabs)
5. [Accordions](#5-accordions)
6. [Comboboxes / Autocomplete](#6-comboboxes--autocomplete)
7. [Menus and Dropdowns](#7-menus-and-dropdowns)
8. [Forms](#8-forms)
9. [Focus Management](#9-focus-management)
10. [Keyboard Navigation](#10-keyboard-navigation)
11. [Live Regions](#11-live-regions)
12. [Color and Contrast](#12-color-and-contrast)
13. [Screen Reader Testing](#13-screen-reader-testing)

---

## 1. General Principles

### Semantic HTML First

- [ ] Use native HTML elements before reaching for ARIA (`<button>` not `<div role="button">`)
- [ ] Use landmarks: `<nav>`, `<main>`, `<aside>`, `<header>`, `<footer>`
- [ ] Use heading hierarchy correctly (`<h1>` through `<h6>`, no skipping levels)
- [ ] Use `<ul>/<ol>` for lists, `<table>` for tabular data

### ARIA Rules

1. **Do not use ARIA if native HTML provides the semantics** -- a `<button>` is always better than `<div role="button">`
2. **Do not change native semantics** -- do not put `role="heading"` on a `<button>`
3. **All interactive ARIA roles must be keyboard accessible**
4. **Do not use `role="presentation"` or `aria-hidden="true"` on focusable elements**
5. **All interactive elements must have an accessible name**

### Required for Every Component

- [ ] Has an accessible name (via content, `aria-label`, `aria-labelledby`, or associated `<label>`)
- [ ] Keyboard operable (all interactions achievable without a mouse)
- [ ] Visible focus indicator on all interactive elements
- [ ] Color is not the sole means of conveying information
- [ ] Text content meets contrast requirements

---

## 2. Buttons

```tsx
// GOOD: Semantic button with accessible name from content
<button onClick={handleSave}>Save changes</button>

// GOOD: Icon button with accessible name
<button onClick={handleClose} aria-label="Close dialog">
  <CloseIcon aria-hidden="true" />
</button>

// GOOD: Button with loading state
<button onClick={handleSubmit} disabled={isLoading} aria-busy={isLoading}>
  {isLoading ? 'Saving...' : 'Save'}
</button>

// GOOD: Toggle button
<button
  onClick={toggleFavorite}
  aria-pressed={isFavorite}
  aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
>
  <HeartIcon aria-hidden="true" />
</button>
```

### Checklist

- [ ] Uses `<button>` element (not `<div>` or `<a>` for actions)
- [ ] Has accessible name (text content or `aria-label`)
- [ ] Icon-only buttons have `aria-label`
- [ ] Decorative icons have `aria-hidden="true"`
- [ ] Toggle buttons use `aria-pressed`
- [ ] Loading buttons use `aria-busy` and update visible text
- [ ] Disabled state uses `disabled` attribute (not just styling)
- [ ] Link-style buttons that navigate use `<a>` instead

---

## 3. Modals / Dialogs

```tsx
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="dialog-title"
  aria-describedby="dialog-description"
>
  <h2 id="dialog-title">Confirm Deletion</h2>
  <p id="dialog-description">
    This action cannot be undone. Are you sure?
  </p>
  <button onClick={onConfirm}>Delete</button>
  <button onClick={onClose}>Cancel</button>
</div>
```

### Checklist

- [ ] Has `role="dialog"` or `role="alertdialog"` (for confirmations requiring immediate response)
- [ ] Has `aria-modal="true"`
- [ ] Has `aria-labelledby` pointing to the dialog title
- [ ] Optionally has `aria-describedby` for additional context
- [ ] Focus moves to dialog when opened (first focusable element or the dialog itself)
- [ ] Focus is trapped within the dialog (Tab/Shift+Tab cycle within)
- [ ] Escape key closes the dialog
- [ ] Focus returns to the trigger element when dialog closes
- [ ] Background content is inert (`inert` attribute or `aria-hidden="true"` on siblings)
- [ ] Clicking the backdrop closes the dialog (optional but expected)
- [ ] Body scroll is prevented while dialog is open

---

## 4. Tabs

```tsx
<div>
  <div role="tablist" aria-label="Account settings">
    <button
      role="tab"
      id="tab-profile"
      aria-selected={activeTab === 'profile'}
      aria-controls="panel-profile"
      tabIndex={activeTab === 'profile' ? 0 : -1}
      onClick={() => setActiveTab('profile')}
    >
      Profile
    </button>
    <button
      role="tab"
      id="tab-security"
      aria-selected={activeTab === 'security'}
      aria-controls="panel-security"
      tabIndex={activeTab === 'security' ? 0 : -1}
      onClick={() => setActiveTab('security')}
    >
      Security
    </button>
  </div>

  <div
    role="tabpanel"
    id="panel-profile"
    aria-labelledby="tab-profile"
    hidden={activeTab !== 'profile'}
    tabIndex={0}
  >
    Profile content...
  </div>
  <div
    role="tabpanel"
    id="panel-security"
    aria-labelledby="tab-security"
    hidden={activeTab !== 'security'}
    tabIndex={0}
  >
    Security content...
  </div>
</div>
```

### Checklist

- [ ] Tab list has `role="tablist"` with `aria-label`
- [ ] Each tab has `role="tab"`
- [ ] Active tab has `aria-selected="true"`, inactive tabs have `aria-selected="false"`
- [ ] Each tab has `aria-controls` pointing to its panel's `id`
- [ ] Only the active tab has `tabIndex={0}`; inactive tabs have `tabIndex={-1}`
- [ ] Each panel has `role="tabpanel"` and `aria-labelledby` pointing to its tab
- [ ] Inactive panels are hidden (`hidden` attribute)
- [ ] Arrow keys move focus between tabs (Left/Right for horizontal, Up/Down for vertical)
- [ ] Home/End keys move to first/last tab
- [ ] Tab key moves focus from tab into the panel

---

## 5. Accordions

```tsx
<div>
  <h3>
    <button
      aria-expanded={isOpen}
      aria-controls="section-1-content"
      id="section-1-header"
      onClick={() => toggle('section-1')}
    >
      Section Title
    </button>
  </h3>
  <div
    id="section-1-content"
    role="region"
    aria-labelledby="section-1-header"
    hidden={!isOpen}
  >
    Section content...
  </div>
</div>
```

### Checklist

- [ ] Trigger is a `<button>` inside a heading element
- [ ] Button has `aria-expanded` reflecting open/closed state
- [ ] Button has `aria-controls` pointing to the content panel
- [ ] Content panel has `role="region"` and `aria-labelledby`
- [ ] Hidden panels use `hidden` attribute
- [ ] Enter/Space toggle the section
- [ ] If multiple sections, arrow keys optionally navigate between headers

---

## 6. Comboboxes / Autocomplete

```tsx
<div>
  <label htmlFor="search-input">Search countries</label>
  <input
    id="search-input"
    role="combobox"
    aria-expanded={isOpen}
    aria-controls="search-listbox"
    aria-activedescendant={highlightedId}
    aria-autocomplete="list"
    autoComplete="off"
  />
  <ul id="search-listbox" role="listbox" aria-label="Countries">
    {results.map((item, index) => (
      <li
        key={item.id}
        id={`option-${item.id}`}
        role="option"
        aria-selected={index === highlightedIndex}
      >
        {item.name}
      </li>
    ))}
  </ul>
</div>
```

### Checklist

- [ ] Input has `role="combobox"`
- [ ] Input has `aria-expanded` (true when listbox is visible)
- [ ] Input has `aria-controls` pointing to the listbox
- [ ] Input has `aria-activedescendant` pointing to the highlighted option's `id`
- [ ] Input has `aria-autocomplete="list"` (or "both" if inline completion)
- [ ] Input has `autoComplete="off"` to prevent browser autocomplete
- [ ] Listbox has `role="listbox"` and `aria-label`
- [ ] Each option has `role="option"` and a unique `id`
- [ ] Selected/highlighted option has `aria-selected="true"`
- [ ] ArrowDown/ArrowUp navigate options
- [ ] Enter selects the highlighted option
- [ ] Escape closes the listbox
- [ ] Typing filters the list and announces result count (via live region)

---

## 7. Menus and Dropdowns

```tsx
<div>
  <button
    aria-haspopup="true"
    aria-expanded={isOpen}
    aria-controls="user-menu"
    onClick={toggleMenu}
  >
    User Options
  </button>
  <ul id="user-menu" role="menu" aria-label="User options">
    <li role="menuitem" tabIndex={-1}>Profile</li>
    <li role="menuitem" tabIndex={-1}>Settings</li>
    <li role="separator" />
    <li role="menuitem" tabIndex={-1}>Sign out</li>
  </ul>
</div>
```

### Checklist

- [ ] Trigger has `aria-haspopup="true"` and `aria-expanded`
- [ ] Menu container has `role="menu"` and `aria-label`
- [ ] Each item has `role="menuitem"` (or `menuitemcheckbox`/`menuitemradio`)
- [ ] Focus moves into menu when opened
- [ ] Arrow keys navigate between items
- [ ] Enter/Space activates the focused item
- [ ] Escape closes the menu and returns focus to trigger
- [ ] Clicking outside closes the menu

---

## 8. Forms

```tsx
// Associate labels with inputs
<label htmlFor="email">Email address</label>
<input id="email" type="email" required aria-describedby="email-hint email-error" />
<span id="email-hint">We will never share your email.</span>
<span id="email-error" role="alert">
  {errors.email && 'Please enter a valid email address.'}
</span>

// Fieldset for groups
<fieldset>
  <legend>Notification preferences</legend>
  <label><input type="checkbox" name="notify-email" /> Email</label>
  <label><input type="checkbox" name="notify-sms" /> SMS</label>
</fieldset>

// Required fields
<label htmlFor="name">
  Name <span aria-hidden="true">*</span>
</label>
<input id="name" required aria-required="true" />
```

### Checklist

- [ ] Every input has an associated `<label>` (via `htmlFor`/`id` or wrapping)
- [ ] Related inputs are grouped with `<fieldset>` and `<legend>`
- [ ] Required fields use `required` attribute and optionally `aria-required`
- [ ] Error messages use `role="alert"` or are announced via live region
- [ ] Inputs reference error/hint text via `aria-describedby`
- [ ] Invalid inputs have `aria-invalid="true"`
- [ ] Submit button is a `<button type="submit">` or `<input type="submit">`
- [ ] Form-level errors are announced and focused

---

## 9. Focus Management

### Focus Trap (Modals, Drawers)

```tsx
import { useEffect, useRef } from 'react';

function useFocusTrap(isActive: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const container = containerRef.current;
    const focusableSelector =
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const focusableElements = container.querySelectorAll<HTMLElement>(focusableSelector);
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    firstFocusable?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

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
    };

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [isActive]);

  return containerRef;
}
```

### Focus Restoration

```tsx
function useRestoreFocus() {
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previousFocus.current = document.activeElement as HTMLElement;
    return () => {
      previousFocus.current?.focus();
    };
  }, []);
}
```

### Checklist

- [ ] Focus moves to new content when it appears (modals, inline alerts)
- [ ] Focus returns to trigger when content is dismissed
- [ ] Focus is trapped within modals and drawers
- [ ] Skip links allow bypassing repetitive navigation
- [ ] `tabIndex={-1}` on programmatically focused non-interactive elements
- [ ] No focus traps in non-modal content
- [ ] Page title updates on route changes (for SPA navigation)

---

## 10. Keyboard Navigation

### Standard Patterns

| Component | Key | Action |
|-----------|-----|--------|
| **Button** | Enter, Space | Activate |
| **Link** | Enter | Navigate |
| **Checkbox** | Space | Toggle |
| **Radio group** | Arrow keys | Move selection |
| **Tabs** | Arrow keys | Switch tab |
| **Menu** | Arrow Down/Up | Navigate items |
| **Menu** | Enter, Space | Activate item |
| **Combobox** | Arrow Down/Up | Navigate options |
| **Combobox** | Enter | Select option |
| **Dialog** | Escape | Close |
| **Dialog** | Tab | Cycle focus within |
| **Accordion** | Enter, Space | Toggle section |
| **Tree** | Arrow Right | Expand / move to child |
| **Tree** | Arrow Left | Collapse / move to parent |

### Implementation Pattern

```tsx
function handleKeyDown(e: React.KeyboardEvent) {
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault(); // Prevent scroll
      focusNext();
      break;
    case 'ArrowUp':
      e.preventDefault();
      focusPrevious();
      break;
    case 'Home':
      e.preventDefault();
      focusFirst();
      break;
    case 'End':
      e.preventDefault();
      focusLast();
      break;
    case 'Enter':
    case ' ':
      e.preventDefault();
      activateItem();
      break;
    case 'Escape':
      close();
      break;
  }
}
```

### Roving tabindex

For composite widgets (tabs, toolbars, menus), only one item is in the tab order at a time:

```tsx
function ToolbarButton({ isActive, ...props }: ToolbarButtonProps) {
  return (
    <button
      tabIndex={isActive ? 0 : -1}
      {...props}
    />
  );
}
```

---

## 11. Live Regions

Announce dynamic content changes to screen readers.

### `aria-live`

```tsx
// Polite: announced after current speech finishes
<div aria-live="polite" aria-atomic="true">
  {searchResults.length} results found
</div>

// Assertive: interrupts current speech (use sparingly)
<div aria-live="assertive" role="alert">
  {errorMessage}
</div>

// Status: equivalent to aria-live="polite" + role="status"
<div role="status">
  Form saved successfully.
</div>
```

### Common Use Cases

| Scenario | Implementation |
|----------|---------------|
| Form validation error | `role="alert"` (assertive) |
| Success notification | `role="status"` (polite) |
| Search result count | `aria-live="polite"` |
| Loading indicator | `aria-live="polite"` + `aria-busy="true"` |
| Chat messages | `aria-live="polite"` on the message container |
| Timer / countdown | `aria-live="off"` with periodic `aria-live="polite"` updates |
| Progress bar | `role="progressbar"` + `aria-valuenow` + `aria-valuemin` + `aria-valuemax` |

### Checklist

- [ ] Dynamic content changes are announced (search results, notifications, errors)
- [ ] Live regions exist in the DOM before content changes (not dynamically inserted)
- [ ] `aria-atomic="true"` when the entire region should be re-read
- [ ] Use `role="alert"` only for urgent errors (not routine notifications)
- [ ] Loading states use `aria-busy="true"` on the updating region
- [ ] Toast/snackbar notifications have `role="status"` or `role="alert"`

---

## 12. Color and Contrast

### WCAG Requirements

| Level | Normal Text | Large Text (18px+ bold, 24px+) | UI Components |
|-------|------------|-------------------------------|---------------|
| **AA** | 4.5:1 | 3:1 | 3:1 |
| **AAA** | 7:1 | 4.5:1 | Not specified |

### Checklist

- [ ] Text meets 4.5:1 contrast ratio against its background (AA)
- [ ] Large text meets 3:1 contrast ratio (AA)
- [ ] UI components (borders, icons, focus indicators) meet 3:1 contrast ratio
- [ ] Color is not the only way to convey information (add icons, text, patterns)
- [ ] Focus indicators are visible (2px+ outline with sufficient contrast)
- [ ] Error states use more than red color (add icon, bold text, or border)
- [ ] Links are distinguishable from surrounding text (underline or 3:1 contrast + non-color indicator)

### React Implementation

```tsx
// DON'T rely on color alone
<span style={{ color: 'red' }}>Error</span>

// DO use multiple indicators
<span role="alert" style={{ color: 'red' }}>
  <ErrorIcon aria-hidden="true" /> Error: Email is required
</span>

// Accessible status indicator
function StatusBadge({ status }: { status: 'active' | 'inactive' }) {
  return (
    <span className={`badge badge-${status}`}>
      <span className="badge-dot" aria-hidden="true" />
      {status === 'active' ? 'Active' : 'Inactive'}
    </span>
  );
}
```

---

## 13. Screen Reader Testing

### Testing Matrix

| Screen Reader | Browser | Platform |
|--------------|---------|----------|
| **VoiceOver** | Safari | macOS, iOS |
| **NVDA** | Firefox, Chrome | Windows |
| **JAWS** | Chrome, Edge | Windows |
| **TalkBack** | Chrome | Android |

### Quick Test Procedure

1. **Tab through the page**: Can you reach all interactive elements? Is the order logical?
2. **Activate every control**: Can you click buttons, toggle checkboxes, select options with keyboard?
3. **Read headings**: Do headings provide a meaningful outline? (VO: `Ctrl+Opt+Cmd+H`)
4. **Read landmarks**: Can you navigate by landmarks? (VO: Web Rotor)
5. **Check forms**: Are all inputs labeled? Are errors announced?
6. **Test dynamic content**: Are notifications, search results, and loading states announced?
7. **Test modals**: Is focus trapped? Does Escape close? Does focus return?

### Automated Testing Tools

```tsx
// jest-axe for unit tests
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

test('Button is accessible', async () => {
  const { container } = render(<Button>Click me</Button>);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

```typescript
// @axe-core/playwright for E2E tests
import AxeBuilder from '@axe-core/playwright';

test('home page has no accessibility violations', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
```

### Common Screen Reader Gotchas

- **Hidden content being read**: Ensure `aria-hidden="true"` or `hidden` attribute on truly hidden content
- **Duplicate announcements**: Avoid redundant `aria-label` that repeats visible text
- **Missing announcements**: Live regions must exist in DOM before content changes
- **Focus order mismatch**: Visual and DOM order must match
- **Image descriptions**: Decorative images need `alt=""` or `aria-hidden="true"`; informative images need descriptive `alt`
