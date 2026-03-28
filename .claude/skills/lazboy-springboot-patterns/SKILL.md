---
name: lazboy-springboot-patterns
description: "Spring Boot patterns for REST APIs, layered services, data access, caching, and async processing. Use this skill when building REST APIs with Spring MVC or WebFlux, structuring controller-service-repository layers, configuring Spring Data JPA, caching, async processing, validation, exception handling, pagination, or production profiles."
version: "1.0.0"
category: Backend
tags: [java, spring-boot, rest-api, jpa, caching, microservices]
---

# Spring Boot Patterns

Production patterns for Spring Boot REST APIs and services.

## 1. REST API Structure

```java
@RestController
@RequestMapping("/api/v1/products")
@RequiredArgsConstructor
public class ProductController {

    private final ProductService productService;

    @GetMapping
    public ResponseEntity<Page<ProductDto>> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "name") String sort) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(sort));
        return ResponseEntity.ok(productService.findAll(pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ProductDto> getById(@PathVariable Long id) {
        return ResponseEntity.ok(productService.findById(id));
    }

    @PostMapping
    public ResponseEntity<ProductDto> create(@Valid @RequestBody CreateProductRequest request) {
        ProductDto created = productService.create(request);
        URI location = URI.create("/api/v1/products/" + created.id());
        return ResponseEntity.created(location).body(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<ProductDto> update(
            @PathVariable Long id,
            @Valid @RequestBody UpdateProductRequest request) {
        return ResponseEntity.ok(productService.update(id, request));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        productService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
```

## 2. Service Layer with Transactions

```java
@Service
@RequiredArgsConstructor
public class ProductService {

    private final ProductRepository productRepository;

    @Transactional(readOnly = true)
    public Page<ProductDto> findAll(Pageable pageable) {
        return productRepository.findAll(pageable).map(ProductDto::from);
    }

    @Transactional(readOnly = true)
    public ProductDto findById(Long id) {
        return productRepository.findById(id)
                .map(ProductDto::from)
                .orElseThrow(() -> new EntityNotFoundException("Product not found: " + id));
    }

    @Transactional
    public ProductDto create(CreateProductRequest request) {
        Product product = Product.builder()
                .name(request.name())
                .price(request.price())
                .category(request.category())
                .build();
        return ProductDto.from(productRepository.save(product));
    }

    @Transactional
    public void delete(Long id) {
        if (!productRepository.existsById(id)) {
            throw new EntityNotFoundException("Product not found: " + id);
        }
        productRepository.deleteById(id);
    }
}
```

## 3. Repository Pattern — Spring Data JPA

```java
public interface ProductRepository extends JpaRepository<Product, Long> {

    Optional<Product> findBySlug(String slug);

    @Query("SELECT p FROM Product p WHERE p.category = :category AND p.price BETWEEN :min AND :max")
    Page<Product> findByCategoryAndPriceRange(
            @Param("category") String category,
            @Param("min") BigDecimal min,
            @Param("max") BigDecimal max,
            Pageable pageable);

    boolean existsBySlug(String slug);
}
```

## 4. DTOs and Validation

```java
// ✅ Record-based DTO — immutable, concise
public record ProductDto(
        Long id,
        String name,
        BigDecimal price,
        String category,
        LocalDateTime createdAt) {

    public static ProductDto from(Product entity) {
        return new ProductDto(
                entity.getId(),
                entity.getName(),
                entity.getPrice(),
                entity.getCategory(),
                entity.getCreatedAt());
    }
}

// ✅ Request with validation
public record CreateProductRequest(
        @NotBlank @Size(max = 100) String name,
        @NotNull @Positive BigDecimal price,
        @NotBlank String category) {}
```

## 5. Exception Handling — @ControllerAdvice

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(EntityNotFoundException.class)
    public ResponseEntity<ProblemDetail> handleNotFound(EntityNotFoundException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setTitle("Resource Not Found");
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ProblemDetail> handleValidation(MethodArgumentNotValidException ex) {
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
        problem.setTitle("Validation Error");

        Map<String, String> errors = new HashMap<>();
        ex.getBindingResult().getFieldErrors().forEach(
                e -> errors.put(e.getField(), e.getDefaultMessage()));
        problem.setProperty("errors", errors);

        return ResponseEntity.badRequest().body(problem);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleGeneral(Exception ex) {
        log.error("Unhandled exception", ex);
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred");
        return ResponseEntity.internalServerError().body(problem);
    }
}
```

## 6. Caching

```java
@Service
@RequiredArgsConstructor
public class ProductService {

    @Cacheable(value = "products", key = "#id")
    public ProductDto findById(Long id) {
        return productRepository.findById(id)
                .map(ProductDto::from)
                .orElseThrow(() -> new EntityNotFoundException("Product not found"));
    }

    @CacheEvict(value = "products", key = "#id")
    public ProductDto update(Long id, UpdateProductRequest request) {
        // update logic
    }

    @CacheEvict(value = "products", allEntries = true)
    public void clearCache() {
        log.info("Product cache cleared");
    }
}
```

## 7. Async Processing

```java
@Configuration
@EnableAsync
public class AsyncConfig {
    @Bean
    public Executor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(5);
        executor.setMaxPoolSize(10);
        executor.setQueueCapacity(50);
        executor.setThreadNamePrefix("async-");
        executor.initialize();
        return executor;
    }
}

@Service
public class NotificationService {

    @Async
    public CompletableFuture<Void> sendNotification(String userId, String message) {
        // Send email/push notification
        log.info("Sending notification to {}", userId);
        return CompletableFuture.completedFuture(null);
    }
}
```

## 8. Structured Logging

```java
@Slf4j
@Service
public class OrderService {

    public OrderDto processOrder(CreateOrderRequest request) {
        log.info("process_order started userId={} items={}", request.userId(), request.items().size());

        try {
            OrderDto order = createOrder(request);
            log.info("process_order completed orderId={} total={}", order.id(), order.total());
            return order;
        } catch (Exception ex) {
            log.error("process_order failed userId={}", request.userId(), ex);
            throw ex;
        }
    }
}
```

## 9. Filters and Middleware

```java
@Component
@Order(1)
public class RequestLoggingFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {
        String requestId = UUID.randomUUID().toString();
        MDC.put("requestId", requestId);
        response.setHeader("X-Request-Id", requestId);

        long start = System.currentTimeMillis();
        try {
            filterChain.doFilter(request, response);
        } finally {
            long duration = System.currentTimeMillis() - start;
            log.info("request method={} path={} status={} duration={}ms",
                    request.getMethod(), request.getRequestURI(), response.getStatus(), duration);
            MDC.clear();
        }
    }
}
```

## 10. Production Best Practices

- **Constructor injection** — never use `@Autowired` on fields
- **`@Transactional(readOnly = true)`** for query-only methods
- **RFC 7807** — enable `spring.mvc.problemdetails.enabled=true` (Spring Boot 3+)
- **HikariCP** — configure pool sizes: `spring.datasource.hikari.maximum-pool-size=10`
- **Profiles** — use `application-{dev,staging,prod}.yml` for environment config
- **Null safety** — use `@NonNull` and `Optional` for return types
- **Keep controllers thin** — delegate all business logic to services

## 11. What NOT to Do

- **No field injection** — use constructor injection with `@RequiredArgsConstructor`
- **No business logic in controllers** — controllers handle HTTP only
- **No `@Transactional` on controllers** — transactions belong in the service layer
- **No raw `Optional.get()`** — use `map()`, `orElseThrow()`, `orElse()`
- **No catching `Exception` broadly** — catch specific exceptions
- **No mutable DTOs** — use records or immutable classes
