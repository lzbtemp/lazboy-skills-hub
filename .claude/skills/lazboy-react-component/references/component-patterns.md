# React Component Patterns

A reference of proven React component patterns with TypeScript examples.

---

## Table of Contents

1. [Compound Components](#1-compound-components)
2. [Render Props](#2-render-props)
3. [Higher-Order Components (HOCs)](#3-higher-order-components-hocs)
4. [Custom Hooks](#4-custom-hooks)
5. [Controlled vs. Uncontrolled](#5-controlled-vs-uncontrolled)
6. [forwardRef](#6-forwardref)
7. [Polymorphic Components](#7-polymorphic-components)
8. [Slot Pattern](#8-slot-pattern)
9. [Headless Components](#9-headless-components)
10. [Error Boundaries](#10-error-boundaries)
11. [Portals](#11-portals)
12. [Pattern Selection Guide](#12-pattern-selection-guide)

---

## 1. Compound Components

Share implicit state between related components. The parent manages state; children consume it via context. Think `<select>` and `<option>`.

```tsx
import { createContext, useContext, useState, type ReactNode } from 'react';

// Context for shared state
interface AccordionContextType {
  openItems: Set<string>;
  toggle: (id: string) => void;
}

const AccordionContext = createContext<AccordionContextType | null>(null);

function useAccordionContext() {
  const context = useContext(AccordionContext);
  if (!context) {
    throw new Error('Accordion components must be used within <Accordion>');
  }
  return context;
}

// Parent component
interface AccordionProps {
  children: ReactNode;
  multiple?: boolean;
}

function Accordion({ children, multiple = false }: AccordionProps) {
  const [openItems, setOpenItems] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setOpenItems((prev) => {
      const next = new Set(multiple ? prev : []);
      if (prev.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <AccordionContext.Provider value={{ openItems, toggle }}>
      <div role="region">{children}</div>
    </AccordionContext.Provider>
  );
}

// Child components
interface AccordionItemProps {
  id: string;
  children: ReactNode;
}

function AccordionItem({ id, children }: AccordionItemProps) {
  return <div data-accordion-item={id}>{children}</div>;
}

function AccordionTrigger({ id, children }: AccordionItemProps) {
  const { openItems, toggle } = useAccordionContext();
  const isOpen = openItems.has(id);

  return (
    <button
      aria-expanded={isOpen}
      aria-controls={`panel-${id}`}
      onClick={() => toggle(id)}
    >
      {children}
    </button>
  );
}

function AccordionPanel({ id, children }: AccordionItemProps) {
  const { openItems } = useAccordionContext();
  const isOpen = openItems.has(id);

  if (!isOpen) return null;
  return (
    <div id={`panel-${id}`} role="region">
      {children}
    </div>
  );
}

// Attach child components as properties
Accordion.Item = AccordionItem;
Accordion.Trigger = AccordionTrigger;
Accordion.Panel = AccordionPanel;

// Usage
function App() {
  return (
    <Accordion multiple>
      <Accordion.Item id="1">
        <Accordion.Trigger id="1">Section 1</Accordion.Trigger>
        <Accordion.Panel id="1">Content for section 1</Accordion.Panel>
      </Accordion.Item>
      <Accordion.Item id="2">
        <Accordion.Trigger id="2">Section 2</Accordion.Trigger>
        <Accordion.Panel id="2">Content for section 2</Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );
}
```

**When to use**: Component families that share state (tabs, accordions, menus, dropdowns, form groups).

---

## 2. Render Props

Pass a function as a prop (or child) to share behavior while letting the consumer control rendering.

```tsx
import { useState, useEffect, type ReactNode } from 'react';

// Render prop component for data fetching
interface FetchProps<T> {
  url: string;
  children: (state: {
    data: T | null;
    loading: boolean;
    error: Error | null;
    refetch: () => void;
  }) => ReactNode;
}

function Fetch<T>({ url, children }: FetchProps<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const json = await response.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [url]);

  return <>{children({ data, loading, error, refetch: fetchData })}</>;
}

// Usage
function UserList() {
  return (
    <Fetch<User[]> url="/api/users">
      {({ data, loading, error, refetch }) => {
        if (loading) return <Spinner />;
        if (error) return <ErrorMessage error={error} onRetry={refetch} />;
        return (
          <ul>
            {data?.map((user) => (
              <li key={user.id}>{user.name}</li>
            ))}
          </ul>
        );
      }}
    </Fetch>
  );
}
```

**When to use**: Sharing behavior with full rendering control. Largely superseded by custom hooks, but still useful for component libraries where you want to provide a component-based API.

---

## 3. Higher-Order Components (HOCs)

A function that takes a component and returns an enhanced component. Common in older codebases; prefer hooks for new code.

```tsx
import { type ComponentType } from 'react';

// HOC that adds loading state
interface WithLoadingProps {
  isLoading: boolean;
}

function withLoading<P extends object>(
  WrappedComponent: ComponentType<P>,
  LoadingComponent: ComponentType = () => <div>Loading...</div>
) {
  function WithLoadingComponent(props: P & WithLoadingProps) {
    const { isLoading, ...restProps } = props;

    if (isLoading) return <LoadingComponent />;
    return <WrappedComponent {...(restProps as P)} />;
  }

  WithLoadingComponent.displayName = `withLoading(${
    WrappedComponent.displayName || WrappedComponent.name || 'Component'
  })`;

  return WithLoadingComponent;
}

// HOC that injects auth context
interface WithAuthProps {
  user: User;
  isAuthenticated: boolean;
}

function withAuth<P extends WithAuthProps>(
  WrappedComponent: ComponentType<P>
) {
  function WithAuthComponent(props: Omit<P, keyof WithAuthProps>) {
    const { user, isAuthenticated } = useAuth();

    if (!isAuthenticated) return <Navigate to="/login" />;

    return (
      <WrappedComponent
        {...(props as P)}
        user={user}
        isAuthenticated={isAuthenticated}
      />
    );
  }

  WithAuthComponent.displayName = `withAuth(${
    WrappedComponent.displayName || WrappedComponent.name
  })`;

  return WithAuthComponent;
}

// Usage
const UserDashboard = withAuth(withLoading(DashboardContent));
```

**When to use**: Cross-cutting concerns in class-based codebases, library wrappers. Prefer hooks for new code.

---

## 4. Custom Hooks

Extract reusable stateful logic into functions. The primary pattern for sharing behavior in modern React.

```tsx
import { useState, useEffect, useCallback, useRef } from 'react';

// Debounced value hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Local storage hook with type safety
function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const nextValue = value instanceof Function ? value(prev) : value;
        window.localStorage.setItem(key, JSON.stringify(nextValue));
        return nextValue;
      });
    },
    [key]
  );

  return [storedValue, setValue];
}

// Media query hook
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(
    () => window.matchMedia(query).matches
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const handler = (event: MediaQueryListEvent) => setMatches(event.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [query]);

  return matches;
}

// Previous value hook
function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}

// Usage
function SearchComponent() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);
  const [favorites, setFavorites] = useLocalStorage<string[]>('favorites', []);
  const isMobile = useMediaQuery('(max-width: 768px)');

  useEffect(() => {
    if (debouncedQuery) {
      // Fetch search results
    }
  }, [debouncedQuery]);

  return (
    <input
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      placeholder={isMobile ? 'Search' : 'Search for items...'}
    />
  );
}
```

---

## 5. Controlled vs. Uncontrolled

### Controlled

Parent owns the state and passes it down. Component is a pure function of its props.

```tsx
interface ControlledInputProps {
  value: string;
  onChange: (value: string) => void;
  label: string;
}

function ControlledInput({ value, onChange, label }: ControlledInputProps) {
  return (
    <label>
      {label}
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

// Usage: parent manages state
function Form() {
  const [name, setName] = useState('');
  return <ControlledInput value={name} onChange={setName} label="Name" />;
}
```

### Uncontrolled

Component manages its own state internally. Parent reads values imperatively (via refs or callbacks).

```tsx
import { useRef } from 'react';

function UncontrolledInput({ label, defaultValue = '' }: {
  label: string;
  defaultValue?: string;
}) {
  return (
    <label>
      {label}
      <input defaultValue={defaultValue} />
    </label>
  );
}

// Usage: parent reads via ref or form submission
function Form() {
  const formRef = useRef<HTMLFormElement>(null);
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(formRef.current!);
    console.log(Object.fromEntries(formData));
  };
  return (
    <form ref={formRef} onSubmit={handleSubmit}>
      <UncontrolledInput label="Name" />
      <button type="submit">Submit</button>
    </form>
  );
}
```

### Hybrid: Support Both

```tsx
interface FlexibleInputProps {
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  label: string;
}

function FlexibleInput({ value, defaultValue, onChange, label }: FlexibleInputProps) {
  const isControlled = value !== undefined;

  return (
    <label>
      {label}
      <input
        {...(isControlled
          ? { value, onChange: (e) => onChange?.(e.target.value) }
          : { defaultValue }
        )}
      />
    </label>
  );
}
```

---

## 6. forwardRef

Expose a DOM element (or imperative handle) from a child component to a parent.

```tsx
import { forwardRef, useRef, useImperativeHandle, type Ref } from 'react';

// Basic forwardRef
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', children, ...props }, ref) => {
    return (
      <button ref={ref} className={`btn btn-${variant}`} {...props}>
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

// useImperativeHandle: expose custom methods
interface InputHandle {
  focus: () => void;
  clear: () => void;
  getValue: () => string;
}

interface FancyInputProps {
  label: string;
  placeholder?: string;
}

const FancyInput = forwardRef<InputHandle, FancyInputProps>(
  ({ label, placeholder }, ref) => {
    const inputRef = useRef<HTMLInputElement>(null);

    useImperativeHandle(ref, () => ({
      focus: () => inputRef.current?.focus(),
      clear: () => {
        if (inputRef.current) inputRef.current.value = '';
      },
      getValue: () => inputRef.current?.value ?? '',
    }));

    return (
      <label>
        {label}
        <input ref={inputRef} placeholder={placeholder} />
      </label>
    );
  }
);
FancyInput.displayName = 'FancyInput';

// Usage
function Form() {
  const inputRef = useRef<InputHandle>(null);

  return (
    <>
      <FancyInput ref={inputRef} label="Search" />
      <button onClick={() => inputRef.current?.focus()}>Focus</button>
      <button onClick={() => inputRef.current?.clear()}>Clear</button>
    </>
  );
}
```

---

## 7. Polymorphic Components

Components that can render as different HTML elements or other components via an `as` prop.

```tsx
import { type ElementType, type ComponentPropsWithoutRef } from 'react';

// Polymorphic component type helper
type PolymorphicProps<E extends ElementType, P = {}> = P &
  Omit<ComponentPropsWithoutRef<E>, keyof P> & {
    as?: E;
  };

// Polymorphic Text component
type TextProps<E extends ElementType = 'span'> = PolymorphicProps<E, {
  size?: 'sm' | 'md' | 'lg';
  weight?: 'normal' | 'bold';
}>;

function Text<E extends ElementType = 'span'>({
  as,
  size = 'md',
  weight = 'normal',
  className,
  ...props
}: TextProps<E>) {
  const Component = as || 'span';
  return (
    <Component
      className={`text-${size} font-${weight} ${className ?? ''}`}
      {...props}
    />
  );
}

// Usage: renders as different elements with correct type checking
function Example() {
  return (
    <>
      <Text>Default span</Text>
      <Text as="p" size="lg">Paragraph</Text>
      <Text as="h1" size="lg" weight="bold">Heading</Text>
      <Text as="a" href="/about">Link</Text>
      <Text as="label" htmlFor="name">Label</Text>
    </>
  );
}
```

**When to use**: Design system primitives (Box, Text, Stack) that should render as semantic HTML while sharing styles.

---

## 8. Slot Pattern

Let consumers inject content into specific "slots" of a component layout.

```tsx
import { type ReactNode } from 'react';

// Card with named slots
interface CardProps {
  header?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  actions?: ReactNode;
}

function Card({ header, children, footer, actions }: CardProps) {
  return (
    <div className="card">
      {header && <div className="card-header">{header}</div>}
      <div className="card-body">{children}</div>
      {actions && <div className="card-actions">{actions}</div>}
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
}

// Layout with slots
interface PageLayoutProps {
  sidebar: ReactNode;
  children: ReactNode;
  topBar?: ReactNode;
}

function PageLayout({ sidebar, children, topBar }: PageLayoutProps) {
  return (
    <div className="layout">
      {topBar && <header className="layout-topbar">{topBar}</header>}
      <aside className="layout-sidebar">{sidebar}</aside>
      <main className="layout-content">{children}</main>
    </div>
  );
}

// Usage
function App() {
  return (
    <PageLayout
      topBar={<Navigation />}
      sidebar={<SideMenu />}
    >
      <Card
        header={<h2>User Profile</h2>}
        actions={
          <>
            <Button variant="secondary">Cancel</Button>
            <Button>Save</Button>
          </>
        }
        footer={<small>Last updated: today</small>}
      >
        <p>Card content goes here.</p>
      </Card>
    </PageLayout>
  );
}
```

---

## 9. Headless Components

Provide logic and state management without any UI. Consumers control all rendering.

```tsx
import { useState, useCallback, useEffect, useRef } from 'react';

// Headless toggle
interface UseToggleReturn {
  isOpen: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
  getTogglerProps: (props?: Record<string, any>) => Record<string, any>;
  getContentProps: () => Record<string, any>;
}

function useToggle(initialState = false): UseToggleReturn {
  const [isOpen, setIsOpen] = useState(initialState);

  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  const getTogglerProps = (props: Record<string, any> = {}) => ({
    'aria-expanded': isOpen,
    onClick: () => {
      toggle();
      props.onClick?.();
    },
    ...props,
  });

  const getContentProps = () => ({
    role: 'region',
    hidden: !isOpen,
  });

  return { isOpen, toggle, open, close, getTogglerProps, getContentProps };
}

// Headless combobox / autocomplete
interface UseComboboxOptions<T> {
  items: T[];
  itemToString: (item: T) => string;
  onSelect?: (item: T) => void;
}

interface UseComboboxReturn<T> {
  inputValue: string;
  filteredItems: T[];
  highlightedIndex: number;
  isOpen: boolean;
  getInputProps: () => Record<string, any>;
  getMenuProps: () => Record<string, any>;
  getItemProps: (index: number) => Record<string, any>;
}

function useCombobox<T>({
  items,
  itemToString,
  onSelect,
}: UseComboboxOptions<T>): UseComboboxReturn<T> {
  const [inputValue, setInputValue] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const filteredItems = items.filter((item) =>
    itemToString(item).toLowerCase().includes(inputValue.toLowerCase())
  );

  const getInputProps = () => ({
    value: inputValue,
    role: 'combobox',
    'aria-expanded': isOpen,
    'aria-autocomplete': 'list' as const,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
      setInputValue(e.target.value);
      setIsOpen(true);
      setHighlightedIndex(-1);
    },
    onFocus: () => setIsOpen(true),
    onKeyDown: (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setHighlightedIndex((i) => Math.min(i + 1, filteredItems.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex((i) => Math.max(i - 1, 0));
          break;
        case 'Enter':
          if (highlightedIndex >= 0) {
            const item = filteredItems[highlightedIndex];
            setInputValue(itemToString(item));
            onSelect?.(item);
            setIsOpen(false);
          }
          break;
        case 'Escape':
          setIsOpen(false);
          break;
      }
    },
  });

  const getMenuProps = () => ({
    role: 'listbox',
    hidden: !isOpen || filteredItems.length === 0,
  });

  const getItemProps = (index: number) => ({
    role: 'option',
    'aria-selected': index === highlightedIndex,
    onClick: () => {
      const item = filteredItems[index];
      setInputValue(itemToString(item));
      onSelect?.(item);
      setIsOpen(false);
    },
  });

  return {
    inputValue,
    filteredItems,
    highlightedIndex,
    isOpen,
    getInputProps,
    getMenuProps,
    getItemProps,
  };
}

// Usage: consumer owns the rendering
function CountryPicker({ countries }: { countries: Country[] }) {
  const {
    inputValue,
    filteredItems,
    highlightedIndex,
    getInputProps,
    getMenuProps,
    getItemProps,
  } = useCombobox({
    items: countries,
    itemToString: (c) => c.name,
    onSelect: (c) => console.log('Selected:', c),
  });

  return (
    <div className="combobox">
      <input {...getInputProps()} placeholder="Search countries..." />
      <ul {...getMenuProps()}>
        {filteredItems.map((country, index) => (
          <li
            key={country.code}
            {...getItemProps(index)}
            className={index === highlightedIndex ? 'highlighted' : ''}
          >
            {country.flag} {country.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

**When to use**: Component libraries that must support diverse visual designs. Separate logic from presentation completely.

---

## 10. Error Boundaries

Catch JavaScript errors in the component tree and display a fallback UI.

```tsx
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.props.onError?.(error, errorInfo);
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      const { fallback } = this.props;
      if (typeof fallback === 'function') {
        return fallback(this.state.error, this.reset);
      }
      return fallback ?? <p>Something went wrong.</p>;
    }
    return this.props.children;
  }
}

// Usage
function App() {
  return (
    <ErrorBoundary
      fallback={(error, reset) => (
        <div role="alert">
          <h2>Something went wrong</h2>
          <pre>{error.message}</pre>
          <button onClick={reset}>Try again</button>
        </div>
      )}
      onError={(error, info) => {
        // Log to error tracking service
        reportError({ error, componentStack: info.componentStack });
      }}
    >
      <Dashboard />
    </ErrorBoundary>
  );
}
```

**Note**: Error boundaries only catch errors during rendering, in lifecycle methods, and in constructors. They do not catch errors in event handlers, async code, or server-side rendering. For those, use try/catch.

---

## 11. Portals

Render children into a DOM node outside the parent component's hierarchy. Essential for modals, tooltips, toasts, and dropdowns that need to escape CSS overflow or stacking contexts.

```tsx
import { createPortal } from 'react-dom';
import { useEffect, useRef, useState, type ReactNode } from 'react';

// Modal using portal
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

function Modal({ isOpen, onClose, title, children }: ModalProps) {
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      previousFocus.current = document.activeElement as HTMLElement;
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.body.style.overflow = '';
      previousFocus.current?.focus();
    };
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-header">
          <h2>{title}</h2>
          <button onClick={onClose} aria-label="Close">x</button>
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>,
    document.body
  );
}

// Usage
function App() {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <>
      <button onClick={() => setIsOpen(true)}>Open Modal</button>
      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="Confirm">
        <p>Are you sure?</p>
      </Modal>
    </>
  );
}
```

---

## 12. Pattern Selection Guide

| Scenario | Recommended Pattern |
|----------|-------------------|
| Related components sharing state | Compound Components |
| Reusable stateful logic | Custom Hooks |
| Logic without UI opinions | Headless Components |
| Rendering as different elements | Polymorphic Components |
| Injecting content into layout | Slot Pattern |
| Catching render errors | Error Boundaries |
| Escaping DOM hierarchy | Portals |
| Exposing DOM ref to parent | forwardRef |
| Cross-cutting concerns (legacy) | HOCs |
| Flexible rendering delegation | Render Props |
| Form state management | Controlled (complex forms) / Uncontrolled (simple forms) |
