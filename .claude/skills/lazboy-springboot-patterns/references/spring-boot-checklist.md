# Spring Boot Production Checklist

Comprehensive checklist for building production-ready Spring Boot applications.
Covers REST API patterns, JPA best practices, caching, async processing,
error handling, security, actuator, and profile management.

---

## 1. REST API Patterns

### Controller Design

- [ ] Controllers annotated with `@RestController`
- [ ] Base path follows `/api/v{version}/{resource}` convention
- [ ] Use `@RequiredArgsConstructor` for constructor injection (never `@Autowired` on fields)
- [ ] Controllers delegate all business logic to service layer
- [ ] No `@Transactional` annotations on controller methods
- [ ] Return `ResponseEntity<T>` for explicit HTTP status control

### HTTP Methods and Status Codes

| Operation | Method | Success Status | Return Type |
|-----------|--------|----------------|-------------|
| List | GET | 200 OK | `Page<Dto>` |
| Get by ID | GET | 200 OK | `Dto` |
| Create | POST | 201 Created | `Dto` + Location header |
| Full update | PUT | 200 OK | `Dto` |
| Partial update | PATCH | 200 OK | `Dto` |
| Delete | DELETE | 204 No Content | `Void` |

### Request Validation

- [ ] All request bodies annotated with `@Valid`
- [ ] Use Bean Validation annotations: `@NotBlank`, `@NotNull`, `@Size`, `@Positive`, `@Email`
- [ ] Use Java records for request/response DTOs (immutable, concise)
- [ ] Custom validators for complex business rules

```java
public record CreateProductRequest(
        @NotBlank @Size(max = 100) String name,
        @NotNull @Positive BigDecimal price,
        @NotBlank String category) {}
```

### Pagination and Sorting

- [ ] Use `Pageable` parameter with sensible defaults
- [ ] Set max page size to prevent abuse: `spring.data.web.pageable.max-page-size=100`
- [ ] Return `Page<T>` which includes total count, page info

```java
@GetMapping
public ResponseEntity<Page<ProductDto>> list(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size,
        @RequestParam(defaultValue = "name") String sort) {
    Pageable pageable = PageRequest.of(page, size, Sort.by(sort));
    return ResponseEntity.ok(productService.findAll(pageable));
}
```

### API Versioning

- [ ] Version in URL path: `/api/v1/`, `/api/v2/`
- [ ] Never break existing versions -- add new endpoints in new versions
- [ ] Document deprecation timeline for old versions

---

## 2. JPA Best Practices

### Entity Design

- [ ] Use Lombok `@Builder`, `@Getter`, `@Setter` (avoid `@Data` on entities)
- [ ] Always define `equals()` and `hashCode()` based on business key (not `@Id`)
- [ ] Use `@CreatedDate` and `@LastModifiedDate` with `@EnableJpaAuditing`
- [ ] Prefer `SEQUENCE` or `IDENTITY` generation strategy (not `TABLE`)

### Relationship Mapping

- [ ] Default to `FetchType.LAZY` for all associations
- [ ] Use `@EntityGraph` or `JOIN FETCH` queries to load associations when needed
- [ ] Avoid bidirectional relationships unless necessary
- [ ] Always set `mappedBy` on the non-owning side
- [ ] Use `orphanRemoval = true` on parent-owned collections

### N+1 Query Prevention

- [ ] Profile queries with `spring.jpa.show-sql=true` in dev
- [ ] Use `@EntityGraph` for known association patterns
- [ ] Use JPQL `JOIN FETCH` for ad-hoc loading
- [ ] Consider `@BatchSize` for collections loaded in loops
- [ ] Enable Hibernate statistics in dev: `spring.jpa.properties.hibernate.generate_statistics=true`

```java
@EntityGraph(attributePaths = {"orderItems", "customer"})
Optional<Order> findWithItemsAndCustomerById(Long id);

@Query("SELECT o FROM Order o JOIN FETCH o.orderItems WHERE o.status = :status")
List<Order> findByStatusWithItems(@Param("status") OrderStatus status);
```

### Repository Patterns

- [ ] Extend `JpaRepository<Entity, IdType>` for full CRUD
- [ ] Use derived query methods for simple queries
- [ ] Use `@Query` with JPQL for complex queries
- [ ] Use `Specification` for dynamic filtering
- [ ] Return `Optional<T>` for single-entity lookups

---

## 3. Caching with @Cacheable

### Setup

- [ ] Add `spring-boot-starter-cache` dependency
- [ ] Annotate config class with `@EnableCaching`
- [ ] Choose cache provider: Caffeine (local), Redis (distributed)

### Annotations

| Annotation | Purpose |
|-----------|---------|
| `@Cacheable` | Cache the return value |
| `@CacheEvict` | Remove entries from cache |
| `@CachePut` | Update cache without skipping execution |
| `@Caching` | Compose multiple cache operations |

### Best Practices

- [ ] Cache read-heavy, write-light data (product catalogs, configs)
- [ ] Always define eviction on write operations
- [ ] Set TTL to prevent stale data: configure in cache manager
- [ ] Use meaningful cache names that reflect the domain
- [ ] Add `@CacheEvict(allEntries = true)` for bulk updates
- [ ] Never cache user-specific mutable data without careful TTL

```java
@Cacheable(value = "products", key = "#id")
public ProductDto findById(Long id) { ... }

@CacheEvict(value = "products", key = "#id")
public ProductDto update(Long id, UpdateProductRequest request) { ... }

@CacheEvict(value = "products", allEntries = true)
public void clearCache() { ... }
```

---

## 4. Async Processing with @Async

### Configuration

- [ ] Create `@Configuration` class with `@EnableAsync`
- [ ] Define a custom `ThreadPoolTaskExecutor` bean
- [ ] Set core/max pool size, queue capacity, thread name prefix
- [ ] Configure rejection policy for overflow

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
        executor.setRejectedExecutionHandler(new CallerRunsPolicy());
        executor.initialize();
        return executor;
    }
}
```

### Usage Rules

- [ ] `@Async` methods must return `void` or `CompletableFuture<T>`
- [ ] `@Async` methods must be `public` and called from a different class
- [ ] Never call `@Async` method from the same class (proxy bypass)
- [ ] Handle exceptions via `AsyncUncaughtExceptionHandler`
- [ ] Propagate MDC context (request IDs) into async threads

---

## 5. Error Handling with @ControllerAdvice

### Global Exception Handler

- [ ] Single `@RestControllerAdvice` class for the application
- [ ] Use RFC 7807 `ProblemDetail` response format (Spring Boot 3+)
- [ ] Enable: `spring.mvc.problemdetails.enabled=true`
- [ ] Map specific exceptions to HTTP status codes
- [ ] Log unhandled exceptions at ERROR level with full stack trace
- [ ] Never expose internal details (stack traces, SQL) in responses

### Exception Mapping

| Exception | HTTP Status | When |
|-----------|-------------|------|
| `EntityNotFoundException` | 404 | Resource not found |
| `MethodArgumentNotValidException` | 400 | Validation failure |
| `DataIntegrityViolationException` | 409 | Duplicate/constraint violation |
| `AccessDeniedException` | 403 | Insufficient permissions |
| `AuthenticationException` | 401 | Not authenticated |
| `Exception` (catch-all) | 500 | Unexpected error |

### Custom Business Exceptions

- [ ] Create a base `BusinessException` extending `RuntimeException`
- [ ] Subclass for each domain error type
- [ ] Include error code, message, and relevant context

---

## 6. Security Configuration

### Spring Security Setup

- [ ] Use `SecurityFilterChain` bean (not extending `WebSecurityConfigurerAdapter`)
- [ ] Configure CORS with allowed origins, methods, headers
- [ ] Enable CSRF for browser clients, disable for pure API services
- [ ] Use `@PreAuthorize` for method-level authorization
- [ ] Store secrets in environment variables, never in code

```java
@Configuration
@EnableMethodSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(csrf -> csrf.disable())  // API-only service
            .sessionManagement(sm -> sm.sessionCreationPolicy(STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/actuator/health").permitAll()
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth -> oauth.jwt(Customizer.withDefaults()))
            .build();
    }
}
```

### Security Checklist

- [ ] JWT validation configured with proper issuer/audience
- [ ] Rate limiting on authentication endpoints
- [ ] Input sanitization for all user inputs
- [ ] SQL injection prevention (parameterized queries only)
- [ ] Sensitive data excluded from logs
- [ ] Security headers set (X-Content-Type-Options, X-Frame-Options)

---

## 7. Actuator Setup

### Dependencies

- [ ] Add `spring-boot-starter-actuator`
- [ ] Add Micrometer registry for your monitoring system (Prometheus, Datadog)

### Configuration

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: when_authorized
      probes:
        enabled: true
  metrics:
    tags:
      application: ${spring.application.name}
```

### Health Checks

- [ ] Liveness probe: `/actuator/health/liveness` (is the app running?)
- [ ] Readiness probe: `/actuator/health/readiness` (can it accept traffic?)
- [ ] Custom health indicators for critical dependencies
- [ ] Configure Kubernetes probes to use actuator endpoints

### Custom Metrics

- [ ] Track business metrics with Micrometer counters/gauges/timers
- [ ] Use `@Timed` annotation for method-level timing
- [ ] Dashboard for key metrics: request rate, error rate, latency p50/p95/p99

---

## 8. Profile Management

### Profile Strategy

| Profile | Purpose | Activation |
|---------|---------|------------|
| `default` | Local development | No profile set |
| `dev` | Development environment | `SPRING_PROFILES_ACTIVE=dev` |
| `staging` | Pre-production | `SPRING_PROFILES_ACTIVE=staging` |
| `prod` | Production | `SPRING_PROFILES_ACTIVE=prod` |
| `test` | Test execution | `@ActiveProfiles("test")` |

### Configuration Files

```
src/main/resources/
  application.yml          # Shared defaults
  application-dev.yml      # Dev overrides
  application-staging.yml  # Staging overrides
  application-prod.yml     # Prod overrides
  application-test.yml     # Test overrides
```

### Best Practices

- [ ] Never put secrets in YAML files -- use environment variables
- [ ] Use `${ENV_VAR:default}` syntax for environment-specific values
- [ ] Keep `application.yml` minimal -- only shared defaults
- [ ] Log active profile at startup for debugging
- [ ] Use `@Profile("prod")` to conditionally load beans
- [ ] Disable debug features in production profile (show-sql, stacktraces)

```yaml
# application.yml
spring:
  datasource:
    url: ${DATABASE_URL:jdbc:h2:mem:testdb}
    hikari:
      maximum-pool-size: ${DB_POOL_SIZE:10}
  jpa:
    show-sql: false
    hibernate:
      ddl-auto: validate
```

---

## 9. Deployment Readiness Checklist

- [ ] All environment-specific config externalized to env vars
- [ ] Graceful shutdown enabled: `server.shutdown=graceful`
- [ ] Connection pool sizes tuned for expected load
- [ ] Health endpoints exposed and probed
- [ ] Structured JSON logging configured
- [ ] Request correlation IDs propagated
- [ ] API documentation generated (SpringDoc/OpenAPI)
- [ ] Database migrations managed with Flyway or Liquibase
- [ ] Docker image uses JRE (not JDK) and non-root user
- [ ] Resource limits set in Kubernetes deployment

---

*Spring Boot Patterns Checklist v1.0 | Aligned with lazboy-springboot-patterns skill*
