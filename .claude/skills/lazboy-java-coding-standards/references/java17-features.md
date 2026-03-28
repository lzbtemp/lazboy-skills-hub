# Java 17+ Features Guide

Reference guide for modern Java features available in Java 17 and later, with
practical examples for Spring Boot services.

## 1. Records

Records are immutable data carriers that auto-generate `equals()`, `hashCode()`,
`toString()`, and accessor methods.

### Basic Record

```java
// Replaces a class with fields, constructor, getters, equals, hashCode, toString
public record Money(BigDecimal amount, Currency currency) {
    // Compact constructor for validation
    public Money {
        Objects.requireNonNull(amount, "amount must not be null");
        Objects.requireNonNull(currency, "currency must not be null");
        if (amount.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("amount must be non-negative");
        }
    }
}

// Usage
var price = new Money(BigDecimal.valueOf(29.99), Currency.getInstance("USD"));
BigDecimal amt = price.amount();  // accessor method (no "get" prefix)
```

### Records as DTOs

```java
// Request DTO with Bean Validation
public record CreateOrderRequest(
    @NotNull Long productId,
    @Positive int quantity,
    @NotBlank String shippingAddress
) {}

// Response DTO with factory method
public record OrderResponse(
    Long id,
    String productName,
    int quantity,
    BigDecimal total,
    OrderStatus status
) {
    public static OrderResponse from(Order order) {
        return new OrderResponse(
            order.getId(),
            order.getProduct().getName(),
            order.getQuantity(),
            order.getTotal(),
            order.getStatus()
        );
    }
}
```

### Records with Custom Methods

```java
public record DateRange(LocalDate start, LocalDate end) {
    public DateRange {
        if (end.isBefore(start)) {
            throw new IllegalArgumentException("end must not be before start");
        }
    }

    public long days() {
        return ChronoUnit.DAYS.between(start, end);
    }

    public boolean contains(LocalDate date) {
        return !date.isBefore(start) && !date.isAfter(end);
    }

    public boolean overlaps(DateRange other) {
        return !this.end.isBefore(other.start) && !other.end.isBefore(this.start);
    }
}
```

**When to use records:** DTOs, value objects, query results, configuration holders,
event payloads. Do NOT use records for JPA entities (they need mutability for proxies).

## 2. Sealed Classes

Sealed classes restrict which classes can extend them, enabling exhaustive pattern
matching.

```java
// Only these three subclasses are allowed
public sealed interface PaymentResult
    permits PaymentSuccess, PaymentDeclined, PaymentError {
}

public record PaymentSuccess(String transactionId, Instant timestamp) implements PaymentResult {}
public record PaymentDeclined(String reason, String code) implements PaymentResult {}
public record PaymentError(Exception cause) implements PaymentResult {}
```

### Exhaustive Handling

```java
// The compiler knows all cases are covered
public String describeResult(PaymentResult result) {
    return switch (result) {
        case PaymentSuccess s -> "Payment successful: " + s.transactionId();
        case PaymentDeclined d -> "Payment declined: " + d.reason();
        case PaymentError e -> "Payment error: " + e.cause().getMessage();
    };
}
```

### Domain Modeling with Sealed Types

```java
public sealed interface Shape permits Circle, Rectangle, Triangle {
    double area();
}

public record Circle(double radius) implements Shape {
    public double area() { return Math.PI * radius * radius; }
}

public record Rectangle(double width, double height) implements Shape {
    public double area() { return width * height; }
}

public record Triangle(double base, double height) implements Shape {
    public double area() { return 0.5 * base * height; }
}
```

## 3. Pattern Matching

### Pattern Matching for instanceof (Java 16+)

```java
// Old style
if (obj instanceof String) {
    String s = (String) obj;
    return s.length();
}

// Modern -- binding variable in the same expression
if (obj instanceof String s) {
    return s.length();
}

// Works in complex conditions
if (obj instanceof String s && s.length() > 5) {
    process(s);
}
```

### Pattern Matching for switch (Java 21+, preview in 17)

```java
// Type pattern switch
public double calculateArea(Shape shape) {
    return switch (shape) {
        case Circle c -> Math.PI * c.radius() * c.radius();
        case Rectangle r -> r.width() * r.height();
        case Triangle t -> 0.5 * t.base() * t.height();
    };
}

// Guarded patterns
public String classify(Object obj) {
    return switch (obj) {
        case Integer i when i < 0 -> "negative integer";
        case Integer i when i == 0 -> "zero";
        case Integer i -> "positive integer";
        case String s when s.isBlank() -> "blank string";
        case String s -> "string: " + s;
        case null -> "null";
        default -> "other: " + obj.getClass().getSimpleName();
    };
}
```

## 4. Text Blocks

Multi-line string literals that preserve formatting.

```java
// SQL query
String query = """
        SELECT m.id, m.name, m.status
        FROM markets m
        WHERE m.status = :status
        ORDER BY m.name
        """;

// JSON template
String json = """
        {
            "name": "%s",
            "email": "%s",
            "role": "USER"
        }
        """.formatted(name, email);

// HTML email template
String html = """
        <html>
          <body>
            <h1>Welcome, %s!</h1>
            <p>Your account has been created successfully.</p>
            <a href="%s">Verify your email</a>
          </body>
        </html>
        """.formatted(userName, verificationLink);
```

**Indentation rules:** The closing `"""` determines the base indentation. Content
to the left of the closing delimiter is preserved as-is.

## 5. Switch Expressions

Switch as an expression that returns a value, with arrow syntax and no fall-through.

```java
// Old style -- verbose, error-prone fall-through
String label;
switch (status) {
    case ACTIVE:
        label = "Active";
        break;
    case INACTIVE:
        label = "Inactive";
        break;
    default:
        label = "Unknown";
}

// Switch expression -- concise, exhaustive, no fall-through
String label = switch (status) {
    case ACTIVE -> "Active";
    case INACTIVE -> "Inactive";
    case PENDING -> "Pending Review";
};

// Multi-line with yield
int priority = switch (severity) {
    case CRITICAL -> 1;
    case HIGH -> 2;
    case MEDIUM -> {
        log.info("Medium severity assigned default priority");
        yield 3;
    }
    case LOW -> 4;
};

// Multiple case labels
String quarter = switch (month) {
    case JANUARY, FEBRUARY, MARCH -> "Q1";
    case APRIL, MAY, JUNE -> "Q2";
    case JULY, AUGUST, SEPTEMBER -> "Q3";
    case OCTOBER, NOVEMBER, DECEMBER -> "Q4";
};
```

## 6. Optional Best Practices

### Return Optional from Query Methods

```java
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
}
```

### Transform with map/flatMap

```java
// Chain transformations
String displayName = userRepository.findByEmail(email)
    .map(User::getDisplayName)
    .orElse("Anonymous");

// flatMap for nested Optionals
Optional<Address> address = userRepository.findByEmail(email)
    .flatMap(user -> Optional.ofNullable(user.getAddress()));
```

### Conditional Execution

```java
// Execute if present
userRepository.findByEmail(email)
    .ifPresent(user -> emailService.sendWelcome(user));

// Execute if present, else run alternative
userRepository.findByEmail(email)
    .ifPresentOrElse(
        user -> log.info("Found user: {}", user.getId()),
        () -> log.warn("User not found for email: {}", email)
    );
```

### What NOT to Do with Optional

```java
// NEVER use Optional as a field type
public class User {
    private Optional<String> nickname;  // BAD
    private String nickname;            // GOOD -- nullable field is fine
}

// NEVER use Optional as a method parameter
public void process(Optional<String> name) {}  // BAD
public void process(@Nullable String name) {}  // GOOD

// NEVER call .get() without checking
user.get().getName();  // BAD -- throws NoSuchElementException

// NEVER use Optional.of() for nullable values
Optional.of(nullableValue);     // BAD -- throws NPE
Optional.ofNullable(nullValue); // GOOD
```

## 7. Stream API Patterns

### Collecting Results

```java
// To unmodifiable list (Java 16+)
List<String> names = users.stream()
    .map(User::getName)
    .toList();  // returns unmodifiable list

// To map
Map<Long, User> userById = users.stream()
    .collect(Collectors.toMap(User::getId, Function.identity()));

// To map with merge function (handle duplicates)
Map<String, User> userByEmail = users.stream()
    .collect(Collectors.toMap(User::getEmail, Function.identity(), (a, b) -> a));

// Grouping
Map<Department, List<User>> byDept = users.stream()
    .collect(Collectors.groupingBy(User::getDepartment));

// Grouping with downstream collector
Map<Department, Long> countByDept = users.stream()
    .collect(Collectors.groupingBy(User::getDepartment, Collectors.counting()));
```

### Filtering and Transforming

```java
// Chained filter + map
List<OrderResponse> activeOrders = orders.stream()
    .filter(o -> o.getStatus() == OrderStatus.ACTIVE)
    .filter(o -> o.getTotal().compareTo(BigDecimal.TEN) > 0)
    .map(OrderResponse::from)
    .toList();

// flatMap for nested collections
List<LineItem> allItems = orders.stream()
    .flatMap(order -> order.getLineItems().stream())
    .toList();

// Distinct and sorted
List<String> uniqueSortedNames = users.stream()
    .map(User::getName)
    .distinct()
    .sorted()
    .toList();
```

### Reducing and Aggregating

```java
// Sum with reduce
BigDecimal total = orders.stream()
    .map(Order::getTotal)
    .reduce(BigDecimal.ZERO, BigDecimal::add);

// Statistics
IntSummaryStatistics stats = orders.stream()
    .mapToInt(Order::getQuantity)
    .summaryStatistics();
// stats.getAverage(), stats.getMax(), stats.getSum()

// Joining strings
String csv = users.stream()
    .map(User::getName)
    .collect(Collectors.joining(", "));
```

### When to Use Streams vs Loops

| Use Streams | Use Loops |
|------------|-----------|
| Simple filter/map/collect chains | Complex logic with early termination |
| Aggregations (groupBy, reduce) | Mutable accumulation with side effects |
| Pipeline under 4-5 operations | Deeply nested transformations |
| Parallel processing of large data | Small collections (< 10 elements) |

## 8. Other Useful Features

### Helpful NullPointerExceptions (Java 14+)

Java now tells you exactly which variable was null:

```
java.lang.NullPointerException: Cannot invoke "String.length()"
  because the return value of "User.getName()" is null
```

### Compact Number Formatting (Java 12+)

```java
var fmt = NumberFormat.getCompactNumberInstance(Locale.US, NumberFormat.Style.SHORT);
fmt.format(1_000);     // "1K"
fmt.format(1_000_000); // "1M"
```

### String Methods

```java
"  hello  ".strip();        // "hello" (Unicode-aware trim)
"  hello  ".stripLeading(); // "hello  "
"hello".repeat(3);          // "hellohellohello"
"line1\nline2".lines();     // Stream<String>
"  ".isBlank();             // true
```
