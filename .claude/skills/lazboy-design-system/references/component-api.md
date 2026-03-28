# Design System Component API Standards

## Prop Naming Conventions

### General Rules

1. **Boolean props** use `is` or `has` prefix for state, bare adjective for visual: `isOpen`, `hasError`, `disabled`, `fullWidth`
2. **Event handler props** use `on` prefix: `onClick`, `onChange`, `onOpenChange`
3. **Render props / slots** use noun or `render` prefix: `icon`, `leftSection`, `renderEmpty`
4. **Variant props** use consistent enum names across all components: `variant`, `size`, `color`
5. **CSS override props**: `className` for root, `classNames` (record) for sub-elements, `style` / `styles` for inline

### Reserved Prop Names

| Prop | Type | Purpose |
|------|------|---------|
| `variant` | string literal union | Visual variant |
| `size` | `'xs' \| 'sm' \| 'md' \| 'lg' \| 'xl'` | Component size |
| `color` | string literal union | Color scheme |
| `disabled` | boolean | Disable interaction |
| `className` | string | Root element class |
| `classNames` | Record<string, string> | Sub-element classes |
| `style` | CSSProperties | Root inline style |
| `styles` | Record<string, CSSProperties> | Sub-element styles |
| `as` | ElementType | Polymorphic element type |
| `ref` | Ref | Forwarded ref |

---

## Composition Patterns

### Polymorphic Components (the `as` Prop)

Allow consumers to change the rendered root element while preserving all component behavior.

```tsx
import { ElementType, ComponentPropsWithoutRef, forwardRef } from 'react';

/**
 * Utility: extract props for a polymorphic component.
 * `C` is the element type, `Props` are the component's own props.
 */
type PolymorphicProps<C extends ElementType, Props = {}> = Props &
  Omit<ComponentPropsWithoutRef<C>, keyof Props> & {
    as?: C;
  };

type PolymorphicRef<C extends ElementType> =
  ComponentPropsWithoutRef<C>['ref'] extends React.Ref<infer T>
    ? React.Ref<T>
    : never;

// Usage: <Button as="a" href="/home">Home</Button>
```

### Ref Forwarding

Every interactive component MUST forward refs to the primary DOM element.

```tsx
const Button = forwardRef<HTMLButtonElement, ButtonProps>((props, ref) => {
  return <button ref={ref} {...props} />;
});
Button.displayName = 'Button';
```

### Controlled vs Uncontrolled

Support both patterns using a `useControllableState` hook.

```tsx
function useControllableState<T>(
  controlledValue: T | undefined,
  defaultValue: T,
  onChange?: (value: T) => void
): [T, (value: T) => void] {
  const isControlled = controlledValue !== undefined;
  const [internalValue, setInternalValue] = useState(defaultValue);
  const value = isControlled ? controlledValue : internalValue;

  const setValue = useCallback(
    (next: T) => {
      if (!isControlled) setInternalValue(next);
      onChange?.(next);
    },
    [isControlled, onChange]
  );

  return [value, setValue];
}
```

Convention:
- `value` + `onChange` = controlled
- `defaultValue` = uncontrolled initial value
- Component works in both modes without additional configuration

### Slot-Based Composition

For complex components, expose named slots rather than deeply nested render props.

```tsx
// Compound component pattern
<Card>
  <Card.Header>
    <Card.Title>Title</Card.Title>
    <Card.Action><IconButton icon={<MoreIcon />} /></Card.Action>
  </Card.Header>
  <Card.Body>Content here</Card.Body>
  <Card.Footer>
    <Button>Save</Button>
  </Card.Footer>
</Card>
```

```tsx
// Slot props pattern (simpler components)
<Input
  leftSection={<SearchIcon />}
  rightSection={<Spinner />}
/>
```

Guidelines:
- Use **compound components** when children have significant internal structure (Card, Tabs, Dialog)
- Use **slot props** when injecting small pieces into fixed positions (Input adornments, Button icons)

---

## TypeScript Interface Definitions

### Button

```tsx
import { ElementType, ComponentPropsWithoutRef, ReactNode, forwardRef } from 'react';

type ButtonVariant = 'solid' | 'outline' | 'ghost' | 'link';
type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
type ButtonColor = 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'neutral';

interface ButtonOwnProps {
  /** Visual style variant */
  variant?: ButtonVariant;
  /** Button size — controls padding, font-size, and min-height */
  size?: ButtonSize;
  /** Color scheme applied to background/border/text */
  color?: ButtonColor;
  /** Renders the button in a loading state with a spinner */
  isLoading?: boolean;
  /** Accessible label shown while loading (replaces visible text for screen readers) */
  loadingText?: string;
  /** Icon displayed before the button label */
  leftIcon?: ReactNode;
  /** Icon displayed after the button label */
  rightIcon?: ReactNode;
  /** Stretches the button to fill its container */
  fullWidth?: boolean;
  /** Disables the button and applies disabled styling */
  disabled?: boolean;
}

type ButtonProps<C extends ElementType = 'button'> = PolymorphicProps<C, ButtonOwnProps>;

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'solid',
      size = 'md',
      color = 'primary',
      isLoading = false,
      loadingText,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled = false,
      as: Component = 'button',
      children,
      className,
      ...rest
    },
    ref
  ) => {
    return (
      <Component
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          buttonStyles({ variant, size, color, fullWidth }),
          className
        )}
        {...rest}
      >
        {isLoading && <Spinner size={size} />}
        {!isLoading && leftIcon && <span className="btn-icon-left">{leftIcon}</span>}
        {isLoading && loadingText ? loadingText : children}
        {!isLoading && rightIcon && <span className="btn-icon-right">{rightIcon}</span>}
      </Component>
    );
  }
);
Button.displayName = 'Button';
```

### Input

```tsx
import { InputHTMLAttributes, ReactNode, forwardRef } from 'react';

type InputSize = 'sm' | 'md' | 'lg';
type InputVariant = 'outline' | 'filled' | 'underline';

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Visual variant of the input */
  variant?: InputVariant;
  /** Input size — controls height, padding, font-size */
  size?: InputSize;
  /** Content rendered inside the input, before the text (e.g., icon) */
  leftSection?: ReactNode;
  /** Content rendered inside the input, after the text (e.g., clear button) */
  rightSection?: ReactNode;
  /** Label displayed above the input */
  label?: ReactNode;
  /** Helper text displayed below the input */
  description?: ReactNode;
  /** Error message — when present, input shows error styling */
  error?: ReactNode;
  /** Makes the input required and shows an asterisk on the label */
  required?: boolean;
  /** Width of the left section in px — adjusts internal padding */
  leftSectionWidth?: number;
  /** Width of the right section in px — adjusts internal padding */
  rightSectionWidth?: number;
  /** Override classes for sub-elements */
  classNames?: {
    root?: string;
    input?: string;
    label?: string;
    description?: string;
    error?: string;
    leftSection?: string;
    rightSection?: string;
  };
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      variant = 'outline',
      size = 'md',
      leftSection,
      rightSection,
      label,
      description,
      error,
      required = false,
      className,
      classNames,
      id: externalId,
      ...rest
    },
    ref
  ) => {
    const id = externalId ?? useId();
    const errorId = error ? `${id}-error` : undefined;
    const descId = description ? `${id}-description` : undefined;

    return (
      <div className={cn('input-root', classNames?.root, className)}>
        {label && (
          <label htmlFor={id} className={cn('input-label', classNames?.label)}>
            {label}
            {required && <span aria-hidden="true"> *</span>}
          </label>
        )}
        <div className="input-wrapper">
          {leftSection && (
            <div className={cn('input-section-left', classNames?.leftSection)}>
              {leftSection}
            </div>
          )}
          <input
            ref={ref}
            id={id}
            aria-invalid={!!error}
            aria-describedby={[errorId, descId].filter(Boolean).join(' ') || undefined}
            className={cn(inputStyles({ variant, size, hasError: !!error }), classNames?.input)}
            {...rest}
          />
          {rightSection && (
            <div className={cn('input-section-right', classNames?.rightSection)}>
              {rightSection}
            </div>
          )}
        </div>
        {description && !error && (
          <p id={descId} className={cn('input-description', classNames?.description)}>
            {description}
          </p>
        )}
        {error && (
          <p id={errorId} role="alert" className={cn('input-error', classNames?.error)}>
            {error}
          </p>
        )}
      </div>
    );
  }
);
Input.displayName = 'Input';
```

### Card

```tsx
import { HTMLAttributes, ReactNode, forwardRef, createContext, useContext } from 'react';

type CardVariant = 'elevated' | 'outline' | 'filled' | 'ghost';
type CardPadding = 'none' | 'sm' | 'md' | 'lg';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Visual variant */
  variant?: CardVariant;
  /** Internal padding */
  padding?: CardPadding;
  /** Adds a hover shadow / lift effect */
  hoverable?: boolean;
  /** Makes the entire card a clickable link target */
  href?: string;
}

interface CardSectionProps extends HTMLAttributes<HTMLDivElement> {
  /** Removes horizontal padding to let content bleed to card edges */
  inheritPadding?: boolean;
  /** Adds a border below the section */
  withBorder?: boolean;
}

const CardContext = createContext<{ padding: CardPadding }>({ padding: 'md' });

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ variant = 'elevated', padding = 'md', hoverable = false, href, children, ...rest }, ref) => {
    const Component = href ? 'a' : 'div';
    return (
      <CardContext.Provider value={{ padding }}>
        <Component
          ref={ref as any}
          href={href}
          className={cn(cardStyles({ variant, padding, hoverable }))}
          {...rest}
        >
          {children}
        </Component>
      </CardContext.Provider>
    );
  }
);
Card.displayName = 'Card';

const CardHeader = forwardRef<HTMLDivElement, CardSectionProps>(
  ({ withBorder = true, children, className, ...rest }, ref) => (
    <div ref={ref} className={cn('card-header', { 'border-b': withBorder }, className)} {...rest}>
      {children}
    </div>
  )
);
CardHeader.displayName = 'Card.Header';

const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ children, className, ...rest }, ref) => (
    <h3 ref={ref} className={cn('card-title', className)} {...rest}>{children}</h3>
  )
);
CardTitle.displayName = 'Card.Title';

const CardBody = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ children, className, ...rest }, ref) => (
    <div ref={ref} className={cn('card-body', className)} {...rest}>{children}</div>
  )
);
CardBody.displayName = 'Card.Body';

const CardFooter = forwardRef<HTMLDivElement, CardSectionProps>(
  ({ withBorder = true, children, className, ...rest }, ref) => (
    <div ref={ref} className={cn('card-footer', { 'border-t': withBorder }, className)} {...rest}>
      {children}
    </div>
  )
);
CardFooter.displayName = 'Card.Footer';

// Attach compound components
const CardNamespace = Object.assign(Card, {
  Header: CardHeader,
  Title: CardTitle,
  Body: CardBody,
  Footer: CardFooter,
  Action: forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ children, className, ...rest }, ref) => (
      <div ref={ref} className={cn('card-action', className)} {...rest}>{children}</div>
    )
  ),
});
```

### Modal (Dialog)

```tsx
import { ReactNode, forwardRef, useEffect, useRef, useCallback } from 'react';

type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';

interface ModalProps {
  /** Whether the modal is visible (controlled) */
  isOpen: boolean;
  /** Called when the modal requests to close (overlay click, Escape, close button) */
  onClose: () => void;
  /** Modal width preset */
  size?: ModalSize;
  /** Title rendered in the modal header */
  title?: ReactNode;
  /** Hides the default close button in the header */
  hideCloseButton?: boolean;
  /** Content rendered in the modal body */
  children: ReactNode;
  /** Content rendered in a sticky footer area */
  footer?: ReactNode;
  /** Prevents closing when clicking the overlay */
  closeOnOverlayClick?: boolean;
  /** Prevents closing when pressing Escape */
  closeOnEsc?: boolean;
  /** Centers the modal vertically */
  centered?: boolean;
  /** Locks body scroll when open */
  lockScroll?: boolean;
  /** Element to return focus to on close (defaults to trigger element) */
  returnFocusRef?: React.RefObject<HTMLElement>;
  /** Override classes for sub-elements */
  classNames?: {
    overlay?: string;
    content?: string;
    header?: string;
    body?: string;
    footer?: string;
    closeButton?: string;
  };
  /** z-index for the overlay */
  zIndex?: number;
}

const Modal = forwardRef<HTMLDivElement, ModalProps>(
  (
    {
      isOpen,
      onClose,
      size = 'md',
      title,
      hideCloseButton = false,
      children,
      footer,
      closeOnOverlayClick = true,
      closeOnEsc = true,
      centered = false,
      lockScroll = true,
      returnFocusRef,
      classNames,
      zIndex = 1000,
    },
    ref
  ) => {
    const contentRef = useRef<HTMLDivElement>(null);

    // Trap focus inside the modal
    useEffect(() => {
      if (!isOpen) return;
      const node = contentRef.current;
      if (!node) return;

      const focusable = node.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      first?.focus();

      const handleTab = (e: KeyboardEvent) => {
        if (e.key !== 'Tab') return;
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      };

      const handleEsc = (e: KeyboardEvent) => {
        if (e.key === 'Escape' && closeOnEsc) onClose();
      };

      document.addEventListener('keydown', handleTab);
      document.addEventListener('keydown', handleEsc);
      return () => {
        document.removeEventListener('keydown', handleTab);
        document.removeEventListener('keydown', handleEsc);
      };
    }, [isOpen, closeOnEsc, onClose]);

    // Lock body scroll
    useEffect(() => {
      if (!isOpen || !lockScroll) return;
      const original = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = original; };
    }, [isOpen, lockScroll]);

    if (!isOpen) return null;

    return (
      <div
        className={cn('modal-overlay', classNames?.overlay)}
        style={{ zIndex }}
        onClick={closeOnOverlayClick ? onClose : undefined}
        aria-hidden="true"
      >
        <div
          ref={mergeRefs(ref, contentRef)}
          role="dialog"
          aria-modal="true"
          aria-label={typeof title === 'string' ? title : undefined}
          className={cn(modalStyles({ size, centered }), classNames?.content)}
          onClick={(e) => e.stopPropagation()}
        >
          {(title || !hideCloseButton) && (
            <div className={cn('modal-header', classNames?.header)}>
              {title && <h2 className="modal-title">{title}</h2>}
              {!hideCloseButton && (
                <button
                  type="button"
                  aria-label="Close"
                  className={cn('modal-close', classNames?.closeButton)}
                  onClick={onClose}
                >
                  &times;
                </button>
              )}
            </div>
          )}
          <div className={cn('modal-body', classNames?.body)}>{children}</div>
          {footer && (
            <div className={cn('modal-footer', classNames?.footer)}>{footer}</div>
          )}
        </div>
      </div>
    );
  }
);
Modal.displayName = 'Modal';
```

### Select

```tsx
import { ReactNode, forwardRef, useState, useRef, useCallback } from 'react';

interface SelectOption {
  /** Unique value for the option */
  value: string;
  /** Display label (falls back to value if not provided) */
  label: string;
  /** Disables this individual option */
  disabled?: boolean;
  /** Optional grouping key */
  group?: string;
  /** Extra data attached to the option (available in onChange) */
  data?: Record<string, unknown>;
}

type SelectSize = 'sm' | 'md' | 'lg';
type SelectVariant = 'outline' | 'filled' | 'underline';

interface SelectProps {
  /** Array of options to display */
  options: SelectOption[];
  /** Currently selected value (controlled) */
  value?: string | null;
  /** Default selected value (uncontrolled) */
  defaultValue?: string | null;
  /** Called when the selected value changes */
  onChange?: (value: string | null, option: SelectOption | null) => void;
  /** Placeholder text shown when nothing is selected */
  placeholder?: string;
  /** Label displayed above the select */
  label?: ReactNode;
  /** Helper text below the select */
  description?: ReactNode;
  /** Error message — triggers error styling */
  error?: ReactNode;
  /** Visual variant */
  variant?: SelectVariant;
  /** Component size */
  size?: SelectSize;
  /** Allow clearing the selection */
  clearable?: boolean;
  /** Enable type-ahead search filtering */
  searchable?: boolean;
  /** Disable the entire select */
  disabled?: boolean;
  /** Mark as required */
  required?: boolean;
  /** Custom render function for each option in the dropdown */
  renderOption?: (option: SelectOption, isSelected: boolean) => ReactNode;
  /** Content rendered in the dropdown when options is empty or search yields no results */
  renderEmpty?: () => ReactNode;
  /** Icon in the left section of the trigger */
  leftSection?: ReactNode;
  /** Maximum height of the dropdown in px */
  maxDropdownHeight?: number;
  /** Override classes for sub-elements */
  classNames?: {
    root?: string;
    trigger?: string;
    dropdown?: string;
    option?: string;
    label?: string;
    description?: string;
    error?: string;
  };
}

const Select = forwardRef<HTMLButtonElement, SelectProps>(
  (
    {
      options,
      value: controlledValue,
      defaultValue = null,
      onChange,
      placeholder = 'Select...',
      label,
      description,
      error,
      variant = 'outline',
      size = 'md',
      clearable = false,
      searchable = false,
      disabled = false,
      required = false,
      renderOption,
      renderEmpty,
      leftSection,
      maxDropdownHeight = 300,
      classNames,
    },
    ref
  ) => {
    const [value, setValue] = useControllableState(controlledValue, defaultValue, (v) => {
      const opt = options.find((o) => o.value === v) ?? null;
      onChange?.(v, opt);
    });

    const [isOpen, setIsOpen] = useState(false);
    const [search, setSearch] = useState('');

    const filtered = searchable && search
      ? options.filter((o) => o.label.toLowerCase().includes(search.toLowerCase()))
      : options;

    const grouped = groupBy(filtered, (o) => o.group ?? '__ungrouped');

    // Keyboard navigation: ArrowUp, ArrowDown, Enter, Escape
    // (implementation abbreviated for brevity)

    return (
      <div className={cn('select-root', classNames?.root)}>
        {label && (
          <label className={cn('select-label', classNames?.label)}>
            {label}
            {required && <span aria-hidden="true"> *</span>}
          </label>
        )}
        <button
          ref={ref}
          type="button"
          role="combobox"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          disabled={disabled}
          className={cn(selectTriggerStyles({ variant, size, hasError: !!error }), classNames?.trigger)}
          onClick={() => setIsOpen((o) => !o)}
        >
          {leftSection}
          <span className="select-value">
            {value ? options.find((o) => o.value === value)?.label : placeholder}
          </span>
          {clearable && value && (
            <span className="select-clear" onClick={(e) => { e.stopPropagation(); setValue(null); }}>
              &times;
            </span>
          )}
          <ChevronDownIcon />
        </button>

        {isOpen && (
          <div
            role="listbox"
            className={cn('select-dropdown', classNames?.dropdown)}
            style={{ maxHeight: maxDropdownHeight }}
          >
            {searchable && (
              <input
                className="select-search"
                placeholder="Search..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                autoFocus
              />
            )}
            {filtered.length === 0 && (renderEmpty ? renderEmpty() : <div className="select-empty">No options</div>)}
            {Object.entries(grouped).map(([group, items]) => (
              <div key={group}>
                {group !== '__ungrouped' && <div className="select-group-label">{group}</div>}
                {items.map((option) => (
                  <div
                    key={option.value}
                    role="option"
                    aria-selected={option.value === value}
                    aria-disabled={option.disabled}
                    className={cn('select-option', classNames?.option, {
                      selected: option.value === value,
                      disabled: option.disabled,
                    })}
                    onClick={() => {
                      if (option.disabled) return;
                      setValue(option.value);
                      setIsOpen(false);
                      setSearch('');
                    }}
                  >
                    {renderOption ? renderOption(option, option.value === value) : option.label}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {description && !error && (
          <p className={cn('select-description', classNames?.description)}>{description}</p>
        )}
        {error && (
          <p role="alert" className={cn('select-error', classNames?.error)}>{error}</p>
        )}
      </div>
    );
  }
);
Select.displayName = 'Select';
```

---

## Accessibility Checklist (All Components)

- [ ] All interactive elements are keyboard navigable
- [ ] Focus is visible and follows a logical order
- [ ] ARIA roles, states, and properties are correct
- [ ] Color contrast meets WCAG 2.1 AA (4.5:1 for text, 3:1 for UI)
- [ ] Screen reader announcements are meaningful
- [ ] Motion respects `prefers-reduced-motion`
- [ ] Touch targets are at least 44x44 CSS px on mobile

## Naming Convention Summary

```
Component:   PascalCase          (Button, TextInput, DatePicker)
Props type:  {Component}Props    (ButtonProps, TextInputProps)
Variant:     {component}Variants (buttonVariants, textInputVariants)
Hook:        use{Feature}        (useControllableState, useDisclosure)
Context:     {Component}Context  (CardContext, TabsContext)
```
