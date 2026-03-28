# React Patterns Reference

Comprehensive guide to React component patterns, state management, and performance
optimization for production applications.

## 1. Component Composition Patterns

### 1.1 Compound Components

Compound components share implicit state through Context, allowing flexible
composition while keeping related logic together.

```typescript
// A compound Select component
interface SelectContextType {
  value: string;
  onChange: (value: string) => void;
  isOpen: boolean;
  toggle: () => void;
}

const SelectContext = createContext<SelectContextType | null>(null);

function useSelectContext() {
  const ctx = useContext(SelectContext);
  if (!ctx) throw new Error("Select compound components must be used within <Select>");
  return ctx;
}

function Select({ value, onChange, children }: {
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const toggle = useCallback(() => setIsOpen(prev => !prev), []);

  return (
    <SelectContext.Provider value={{ value, onChange, isOpen, toggle }}>
      <div className="select-wrapper">{children}</div>
    </SelectContext.Provider>
  );
}

function SelectTrigger({ children }: { children: ReactNode }) {
  const { toggle, value } = useSelectContext();
  return (
    <button onClick={toggle} aria-haspopup="listbox">
      {children ?? value}
    </button>
  );
}

function SelectOption({ value, children }: { value: string; children: ReactNode }) {
  const { onChange, value: selected, toggle } = useSelectContext();
  return (
    <li
      role="option"
      aria-selected={selected === value}
      onClick={() => { onChange(value); toggle(); }}
    >
      {children}
    </li>
  );
}

// Attach sub-components
Select.Trigger = SelectTrigger;
Select.Option = SelectOption;
```

**When to use:** Component groups that share state (Tabs, Accordions, Menus, Form
Fields). Avoids prop drilling between related elements.

### 1.2 Render Props

Render props delegate rendering control to the consumer while encapsulating logic.

```typescript
interface MouseTrackerProps {
  children: (position: { x: number; y: number }) => ReactNode;
}

function MouseTracker({ children }: MouseTrackerProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handler = (e: MouseEvent) => setPosition({ x: e.clientX, y: e.clientY });
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, []);

  return <>{children(position)}</>;
}

// Usage
<MouseTracker>
  {({ x, y }) => <Tooltip style={{ left: x, top: y }}>Cursor here</Tooltip>}
</MouseTracker>
```

**When to use:** When you need to share behavior but the consumer controls the
rendering. Useful for cross-cutting concerns like tracking, data fetching, and
feature flags.

### 1.3 Higher-Order Components (HOCs)

HOCs wrap a component to inject props or behavior. Use sparingly in modern React
-- prefer hooks for most cases.

```typescript
function withAuth<P extends object>(WrappedComponent: ComponentType<P>) {
  return function AuthenticatedComponent(props: P) {
    const { user, loading } = useAuth();

    if (loading) return <Spinner />;
    if (!user) return <Navigate to="/login" />;

    return <WrappedComponent {...props} />;
  };
}

const ProtectedDashboard = withAuth(Dashboard);
```

**When to use:** Wrapping third-party components you cannot modify, or applying
decorators (logging, error boundaries) at the route level. Prefer hooks for new code.

## 2. Custom Hook Patterns

### 2.1 Data Fetching Hook

```typescript
interface UseQueryOptions<T> {
  enabled?: boolean;
  refetchInterval?: number;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

interface UseQueryResult<T> {
  data: T | undefined;
  error: Error | undefined;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

function useQuery<T>(url: string, options: UseQueryOptions<T> = {}): UseQueryResult<T> {
  const { enabled = true, refetchInterval, onSuccess, onError } = options;
  const [data, setData] = useState<T | undefined>();
  const [error, setError] = useState<Error | undefined>();
  const [isLoading, setIsLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!enabled) return;
    setIsLoading(true);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(undefined);
      onSuccess?.(json);
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err));
      setError(e);
      onError?.(e);
    } finally {
      setIsLoading(false);
    }
  }, [url, enabled, onSuccess, onError]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!refetchInterval || !enabled) return;
    const id = setInterval(fetchData, refetchInterval);
    return () => clearInterval(id);
  }, [refetchInterval, enabled, fetchData]);

  return { data, error, isLoading, isError: !!error, refetch: fetchData };
}
```

### 2.2 Local Storage Hook

```typescript
function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback((value: T | ((prev: T) => T)) => {
    setStoredValue(prev => {
      const next = value instanceof Function ? value(prev) : value;
      window.localStorage.setItem(key, JSON.stringify(next));
      return next;
    });
  }, [key]);

  return [storedValue, setValue];
}
```

### 2.3 Media Query Hook

```typescript
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia(query).matches : false
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);

  return matches;
}

// Usage
const isMobile = useMediaQuery("(max-width: 768px)");
```

## 3. State Management Patterns

### 3.1 Context + useReducer (Built-in)

Best for moderate complexity where external libraries are overkill.

```typescript
// Define granular contexts to avoid unnecessary re-renders
const UserContext = createContext<User | null>(null);
const UserDispatchContext = createContext<Dispatch<UserAction>>(() => {});

function UserProvider({ children }: { children: ReactNode }) {
  const [user, dispatch] = useReducer(userReducer, null);
  return (
    <UserContext.Provider value={user}>
      <UserDispatchContext.Provider value={dispatch}>
        {children}
      </UserDispatchContext.Provider>
    </UserContext.Provider>
  );
}
```

**Key rule:** Split state and dispatch into separate contexts so components that
only dispatch do not re-render when state changes.

### 3.2 Zustand (Lightweight External Store)

```typescript
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface CartStore {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  clearCart: () => void;
  totalPrice: () => number;
}

const useCartStore = create<CartStore>()(
  devtools(
    persist(
      (set, get) => ({
        items: [],
        addItem: (item) => set((state) => ({ items: [...state.items, item] })),
        removeItem: (id) => set((state) => ({
          items: state.items.filter((i) => i.id !== id),
        })),
        clearCart: () => set({ items: [] }),
        totalPrice: () => get().items.reduce((sum, i) => sum + i.price * i.qty, 0),
      }),
      { name: "cart-storage" }
    )
  )
);

// Usage -- only subscribes to items, not the whole store
const items = useCartStore((state) => state.items);
```

### 3.3 Redux Toolkit (Complex Global State)

```typescript
import { createSlice, configureStore, createAsyncThunk } from "@reduxjs/toolkit";

// Async thunk for API calls
export const fetchProducts = createAsyncThunk(
  "products/fetch",
  async (category: string, { rejectWithValue }) => {
    try {
      const res = await fetch(`/api/products?category=${category}`);
      if (!res.ok) throw new Error("Failed to fetch");
      return await res.json();
    } catch (err) {
      return rejectWithValue((err as Error).message);
    }
  }
);

const productsSlice = createSlice({
  name: "products",
  initialState: { items: [] as Product[], status: "idle" as "idle" | "loading" | "failed", error: null as string | null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchProducts.pending, (state) => { state.status = "loading"; })
      .addCase(fetchProducts.fulfilled, (state, action) => {
        state.status = "idle";
        state.items = action.payload;
      })
      .addCase(fetchProducts.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload as string;
      });
  },
});

export const store = configureStore({
  reducer: { products: productsSlice.reducer },
});
```

## 4. Performance Optimization

### 4.1 React.memo

Wrap components that receive the same props frequently but whose parent re-renders often.

```typescript
const ExpensiveList = React.memo(function ExpensiveList({ items }: { items: Item[] }) {
  return (
    <ul>
      {items.map((item) => (
        <li key={item.id}>{item.name}</li>
      ))}
    </ul>
  );
});
```

**Do not** memo everything. Only memo components where profiling shows wasted renders.

### 4.2 useMemo and useCallback

```typescript
// useMemo: cache expensive derived values
const filteredData = useMemo(
  () => data.filter((d) => d.category === selectedCategory).sort((a, b) => a.name.localeCompare(b.name)),
  [data, selectedCategory]
);

// useCallback: stable function references for child props
const handleDelete = useCallback(
  (id: string) => dispatch({ type: "DELETE", payload: id }),
  [dispatch]
);
```

### 4.3 Lazy Loading and Code Splitting

```typescript
const AdminPanel = lazy(() => import("./pages/AdminPanel"));
const Analytics = lazy(() => import("./pages/Analytics"));

function AppRoutes() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/admin" element={<AdminPanel />} />
        <Route path="/analytics" element={<Analytics />} />
      </Routes>
    </Suspense>
  );
}
```

### 4.4 Virtualization for Large Lists

Use `@tanstack/react-virtual` or `react-window` for lists exceeding 100 items.

```typescript
import { FixedSizeList } from "react-window";

function VirtualizedTable({ rows }: { rows: Row[] }) {
  return (
    <FixedSizeList height={600} width="100%" itemCount={rows.length} itemSize={48}>
      {({ index, style }) => (
        <div style={style} className="table-row">
          {rows[index].name}
        </div>
      )}
    </FixedSizeList>
  );
}
```

### 4.5 Avoiding Common Performance Pitfalls

```typescript
// BAD: inline object creates new reference every render
<MyComponent style={{ color: "red" }} />

// GOOD: stable reference
const redStyle = useMemo(() => ({ color: "red" }), []);
<MyComponent style={redStyle} />

// BAD: inline function in JSX
<button onClick={() => handleClick(id)}>Click</button>

// GOOD: stable callback
const onClick = useCallback(() => handleClick(id), [id]);
<button onClick={onClick}>Click</button>

// BAD: deriving state in useEffect
useEffect(() => {
  setFilteredItems(items.filter(i => i.active));
}, [items]);

// GOOD: derive during render
const filteredItems = useMemo(() => items.filter(i => i.active), [items]);
```

## 5. Error Handling Patterns

### 5.1 Error Boundaries

```typescript
class ErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    reportError(error, info);
  }

  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}
```

### 5.2 Suspense for Data Fetching

```typescript
// With React 18+ and a Suspense-compatible data library
function ProductPage({ id }: { id: string }) {
  return (
    <ErrorBoundary fallback={<ErrorMessage />}>
      <Suspense fallback={<ProductSkeleton />}>
        <ProductDetails id={id} />
      </Suspense>
    </ErrorBoundary>
  );
}
```

## 6. Decision Matrix

| Scenario | Recommended Pattern |
|----------|-------------------|
| Shared state between 2-3 siblings | Lift state up |
| Shared state across distant components | Context + useReducer |
| Complex global state with middleware | Redux Toolkit |
| Simple global state, minimal boilerplate | Zustand |
| Reusable behavior logic | Custom hooks |
| Flexible child rendering | Compound components |
| Cross-cutting concerns (auth, logging) | HOC or custom hook |
| Expensive list rendering | Virtualization |
| Route-level code splitting | React.lazy + Suspense |
