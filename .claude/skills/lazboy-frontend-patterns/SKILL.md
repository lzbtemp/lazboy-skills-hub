---
name: lazboy-frontend-patterns
description: "React and Next.js patterns for component composition, state management, performance optimization, and accessible UI development. Use this skill when building React components, managing application state, implementing data fetching, optimizing render performance, handling forms, or creating accessible interactive patterns."
version: "1.0.0"
category: Frontend
tags: [react, nextjs, typescript, components, state-management, accessibility]
---

# Frontend Development Patterns

Production-ready React and Next.js patterns for scalable applications.

## 1. Component Composition

### Compound Components

Use Context to create interdependent component groups:

```typescript
interface TabsContextType {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const TabsContext = createContext<TabsContextType | null>(null);

function Tabs({ children, defaultTab }: { children: ReactNode; defaultTab: string }) {
  const [activeTab, setActiveTab] = useState(defaultTab);
  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      {children}
    </TabsContext.Provider>
  );
}

function TabList({ children }: { children: ReactNode }) {
  return <div role="tablist">{children}</div>;
}

function Tab({ id, children }: { id: string; children: ReactNode }) {
  const { activeTab, setActiveTab } = useContext(TabsContext)!;
  return (
    <button role="tab" aria-selected={activeTab === id} onClick={() => setActiveTab(id)}>
      {children}
    </button>
  );
}

function TabPanel({ id, children }: { id: string; children: ReactNode }) {
  const { activeTab } = useContext(TabsContext)!;
  if (activeTab !== id) return null;
  return <div role="tabpanel">{children}</div>;
}

// Usage
<Tabs defaultTab="overview">
  <TabList>
    <Tab id="overview">Overview</Tab>
    <Tab id="details">Details</Tab>
  </TabList>
  <TabPanel id="overview">Overview content</TabPanel>
  <TabPanel id="details">Details content</TabPanel>
</Tabs>
```

### Render Props

```typescript
interface DataFetcherProps<T> {
  url: string;
  children: (data: T | null, loading: boolean, error: Error | null) => ReactNode;
}

function DataFetcher<T>({ url, children }: DataFetcherProps<T>) {
  const { data, loading, error } = useQuery<T>(url);
  return <>{children(data, loading, error)}</>;
}
```

## 2. Custom Hooks

### useToggle

```typescript
function useToggle(initial = false): [boolean, () => void] {
  const [value, setValue] = useState(initial);
  const toggle = useCallback(() => setValue(prev => !prev), []);
  return [value, toggle];
}
```

### useQuery — Async Data Fetching

```typescript
function useQuery<T>(url: string, options?: { enabled?: boolean }) {
  const [state, setState] = useState<{
    data: T | null;
    loading: boolean;
    error: Error | null;
  }>({ data: null, loading: true, error: null });

  useEffect(() => {
    if (options?.enabled === false) return;

    let cancelled = false;
    setState(prev => ({ ...prev, loading: true }));

    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch(error => {
        if (!cancelled) setState({ data: null, loading: false, error });
      });

    return () => { cancelled = true; };
  }, [url, options?.enabled]);

  return state;
}
```

### useDebounce

```typescript
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
```

## 3. State Management — Context + Reducer

```typescript
interface AppState {
  user: User | null;
  theme: 'light' | 'dark';
  notifications: Notification[];
}

type AppAction =
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'TOGGLE_THEME' }
  | { type: 'ADD_NOTIFICATION'; payload: Notification }
  | { type: 'DISMISS_NOTIFICATION'; payload: string };

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_USER':
      return { ...state, user: action.payload };
    case 'TOGGLE_THEME':
      return { ...state, theme: state.theme === 'light' ? 'dark' : 'light' };
    case 'ADD_NOTIFICATION':
      return { ...state, notifications: [...state.notifications, action.payload] };
    case 'DISMISS_NOTIFICATION':
      return { ...state, notifications: state.notifications.filter(n => n.id !== action.payload) };
    default:
      return state;
  }
}

const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
} | null>(null);

function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, {
    user: null,
    theme: 'light',
    notifications: [],
  });
  return <AppContext.Provider value={{ state, dispatch }}>{children}</AppContext.Provider>;
}

function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
}
```

## 4. Performance Optimization

### Memoization

```typescript
// ✅ Memoize expensive computations
const sortedItems = useMemo(
  () => items.sort((a, b) => b.score - a.score),
  [items],
);

// ✅ Stable callback references
const handleSelect = useCallback(
  (id: string) => dispatch({ type: 'SELECT', payload: id }),
  [dispatch],
);

// ✅ Prevent re-renders of pure components
const MemoizedCard = React.memo(function Card({ item }: { item: Item }) {
  return <div>{item.name}</div>;
});
```

### Code Splitting

```typescript
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  );
}
```

### List Virtualization

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
  });

  return (
    <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.key}
            style={{
              position: 'absolute',
              top: 0,
              transform: `translateY(${virtualRow.start}px)`,
              height: `${virtualRow.size}px`,
            }}
          >
            {items[virtualRow.index].name}
          </div>
        ))}
      </div>
    </div>
  );
}
```

## 5. Form Handling

```typescript
interface FormState {
  values: Record<string, string>;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
}

function useForm(initialValues: Record<string, string>, validate: (values: Record<string, string>) => Record<string, string>) {
  const [state, setState] = useState<FormState>({
    values: initialValues,
    errors: {},
    touched: {},
  });

  const handleChange = (name: string, value: string) => {
    setState(prev => ({
      ...prev,
      values: { ...prev.values, [name]: value },
    }));
  };

  const handleBlur = (name: string) => {
    setState(prev => ({
      ...prev,
      touched: { ...prev.touched, [name]: true },
      errors: validate(prev.values),
    }));
  };

  const handleSubmit = (onSubmit: (values: Record<string, string>) => void) => {
    const errors = validate(state.values);
    if (Object.keys(errors).length === 0) {
      onSubmit(state.values);
    } else {
      setState(prev => ({ ...prev, errors, touched: Object.fromEntries(Object.keys(prev.values).map(k => [k, true])) }));
    }
  };

  return { ...state, handleChange, handleBlur, handleSubmit };
}
```

## 6. Accessibility

### Keyboard Navigation

```typescript
function useKeyboardNavigation(items: string[], onSelect: (item: string) => void) {
  const [activeIndex, setActiveIndex] = useState(0);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex(prev => Math.min(prev + 1, items.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        onSelect(items[activeIndex]);
        break;
      case 'Escape':
        setActiveIndex(0);
        break;
    }
  }, [items, activeIndex, onSelect]);

  return { activeIndex, handleKeyDown };
}
```

### Error Boundary

```typescript
class ErrorBoundary extends React.Component<
  { children: ReactNode; fallback: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}
```

## 7. What NOT to Do

- **No prop drilling** beyond 2 levels — use Context or composition
- **No inline object/array literals** in JSX props — causes unnecessary re-renders
- **No `useEffect` for derived state** — compute during render with `useMemo`
- **No uncontrolled side effects** — cleanup all subscriptions and timers
- **No missing key props** — always use stable, unique keys in lists
- **No accessibility shortcuts** — always include ARIA attributes and keyboard handling
