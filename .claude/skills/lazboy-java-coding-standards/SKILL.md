---
name: lazboy-java-coding-standards
description: "Coding standards for readable, maintainable Java 17+ in Spring Boot services. Use this skill when writing or reviewing Java code, enforcing naming conventions, immutability, exception handling, Optional/streams usage, or structuring packages. Triggers on any Java development, code review, or Spring Boot project work."
version: "1.0.0"
category: Code Quality
tags: [java, spring-boot, coding-standards, records, streams, testing]
---

# Java Coding Standards

Standards for readable, maintainable Java 17+ code in Spring Boot services.

## 1. Core Principles

1. Prefer clarity over cleverness
2. Immutable by default — minimize shared mutable state
3. Fail fast with meaningful exceptions
4. Consistent naming and package structure

## 2. Naming Conventions

```java
// Classes/Records — PascalCase
public class MarketService {}
public record Money(BigDecimal amount, Currency currency) {}

// Methods/Fields — camelCase
private final MarketRepository marketRepository;
public Market findBySlug(String slug) {}

// Constants — UPPER_SNAKE_CASE
private static final int MAX_PAGE_SIZE = 100;
private static final Duration CACHE_TTL = Duration.ofMinutes(5);
```

## 3. Immutability

Favor records and final fields:

```java
// ✅ Record — immutable, concise
public record MarketDto(Long id, String name, MarketStatus status) {}

// ✅ Immutable class with final fields
public class Market {
    private final Long id;
    private final String name;
    private final MarketStatus status;

    public Market(Long id, String name, MarketStatus status) {
        this.id = id;
        this.name = name;
        this.status = status;
    }

    // Getters only — no setters
    public Long getId() { return id; }
    public String getName() { return name; }
    public MarketStatus getStatus() { return status; }
}
```

## 4. Optional Usage

Return `Optional` from find methods. Use `map`/`flatMap` — never raw `get()`:

```java
// ✅ Return Optional from repository
Optional<Market> findBySlug(String slug);

// ✅ Transform with map/flatMap
return marketRepository.findBySlug(slug)
        .map(MarketDto::from)
        .orElseThrow(() -> new MarketNotFoundException(slug));

// ❌ Never call get() without checking
Market market = marketRepository.findBySlug(slug).get(); // throws if absent!
```

## 5. Streams Best Practices

Keep pipelines short and readable:

```java
// ✅ Short, clear pipeline
List<String> names = markets.stream()
        .map(Market::name)
        .filter(Objects::nonNull)
        .toList();

// ✅ Collecting to map
Map<Long, Market> marketById = markets.stream()
        .collect(Collectors.toMap(Market::id, Function.identity()));
```

Avoid complex nested streams — prefer loops for clarity when the pipeline exceeds 4-5 operations.

## 6. Exception Handling

Use unchecked exceptions for domain errors. Create domain-specific types:

```java
// ✅ Domain exception hierarchy
public class DomainException extends RuntimeException {
    public DomainException(String message) { super(message); }
    public DomainException(String message, Throwable cause) { super(message, cause); }
}

public class MarketNotFoundException extends DomainException {
    public MarketNotFoundException(String slug) {
        super("Market not found: " + slug);
    }
}

public class InsufficientFundsException extends DomainException {
    public InsufficientFundsException(BigDecimal required, BigDecimal available) {
        super("Insufficient funds: required=%s, available=%s".formatted(required, available));
    }
}
```

```java
// ✅ Wrap technical exceptions with context
try {
    return objectMapper.readValue(json, Market.class);
} catch (JsonProcessingException ex) {
    throw new DomainException("Failed to parse market data", ex);
}

// ❌ Avoid broad catch(Exception)
try { ... } catch (Exception ex) { /* swallowed! */ }
```

## 7. Generics and Type Safety

Avoid raw types. Prefer bounded generics:

```java
// ✅ Bounded generic — type-safe
public <T extends Identifiable> Map<Long, T> indexById(Collection<T> items) {
    return items.stream()
            .collect(Collectors.toMap(Identifiable::getId, Function.identity()));
}

// ❌ Raw type
List list = new ArrayList();  // No type safety
```

## 8. Project Structure

```
src/main/java/com/lazboy/app/
├── config/           # Spring configuration
├── controller/       # REST controllers (thin)
├── service/          # Business logic
├── repository/       # Data access
├── domain/           # Entities and value objects
├── dto/              # Request/response DTOs
└── exception/        # Custom exceptions
src/main/resources/
├── application.yml
├── application-dev.yml
└── application-prod.yml
src/test/java/        # Mirrors main structure
```

## 9. Formatting and Style

- Use 4 spaces consistently (no tabs)
- One public top-level type per file
- Keep methods short and focused — extract helpers for clarity
- Member order: constants → fields → constructors → public methods → private methods

## 10. Logging

```java
// ✅ SLF4J with structured key=value format
private static final Logger log = LoggerFactory.getLogger(MarketService.class);

log.info("fetch_market slug={}", slug);
log.warn("market_not_found slug={}", slug);
log.error("fetch_market_failed slug={}", slug, ex);

// ❌ String concatenation in log statements
log.info("Fetching market: " + slug);  // Always evaluates, even if level disabled
```

## 11. Null Handling

- Use `@NonNull` annotations on parameters and return types
- Accept `@Nullable` only when unavoidable
- Use Bean Validation (`@NotNull`, `@NotBlank`) on request DTOs

```java
// ✅ Explicit null contract
public MarketDto findById(@NonNull Long id) {
    return marketRepository.findById(id)
            .map(MarketDto::from)
            .orElseThrow(() -> new MarketNotFoundException(id.toString()));
}
```

## 12. Testing

Use JUnit 5 + AssertJ + Mockito:

```java
@ExtendWith(MockitoExtension.class)
class MarketServiceTest {

    @Mock
    private MarketRepository marketRepository;

    @InjectMocks
    private MarketService marketService;

    @Test
    void shouldReturnMarket_whenSlugExists() {
        // Arrange
        Market market = new Market(1L, "test-market", MarketStatus.ACTIVE);
        when(marketRepository.findBySlug("test-market")).thenReturn(Optional.of(market));

        // Act
        MarketDto result = marketService.findBySlug("test-market");

        // Assert
        assertThat(result.name()).isEqualTo("test-market");
        assertThat(result.status()).isEqualTo(MarketStatus.ACTIVE);
    }

    @Test
    void shouldThrow_whenSlugNotFound() {
        when(marketRepository.findBySlug("missing")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> marketService.findBySlug("missing"))
                .isInstanceOf(MarketNotFoundException.class)
                .hasMessageContaining("missing");
    }
}
```

## 13. Code Smells to Avoid

| Smell | Fix |
|-------|-----|
| Long parameter lists | Use DTO or builder |
| Deep nesting | Early returns |
| Magic numbers | Named constants |
| Static mutable state | Dependency injection |
| Silent catch blocks | Log and rethrow |
| Field injection (`@Autowired`) | Constructor injection |
| Mutable DTOs with setters | Records or immutable classes |

## 14. Summary

> Keep code intentional, typed, and observable. Optimize for maintainability
> over micro-optimizations unless proven necessary.
