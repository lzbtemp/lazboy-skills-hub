# Spring Boot Testing Guide

Comprehensive guide to testing Spring Boot applications: test slicing, MockMvc,
TestContainers, integration testing, and best practices.

---

## 1. Test Slicing Overview

Spring Boot provides test slice annotations that load only the parts of the
application context needed for a specific layer. This makes tests faster and
more focused than loading the full context with `@SpringBootTest`.

| Annotation | What It Loads | Use For |
|-----------|---------------|---------|
| `@WebMvcTest` | Controllers, filters, advice | REST endpoint testing |
| `@DataJpaTest` | JPA repositories, entities | Repository/query testing |
| `@WebFluxTest` | WebFlux controllers | Reactive endpoint testing |
| `@JsonTest` | JSON serialization | DTO serialization testing |
| `@RestClientTest` | REST clients | External API client testing |
| `@SpringBootTest` | Full context | Integration/end-to-end testing |

### When to Use What

- **Unit test a controller** -- `@WebMvcTest(ProductController.class)`
- **Unit test a repository query** -- `@DataJpaTest`
- **Test the full request lifecycle** -- `@SpringBootTest` with `TestRestTemplate`
- **Test with real database** -- `@SpringBootTest` + TestContainers

---

## 2. @WebMvcTest -- Controller Testing

`@WebMvcTest` loads only the web layer: controllers, `@ControllerAdvice`,
filters, and converters. Service and repository beans are NOT loaded --
you mock them.

### Basic Controller Test

```java
@WebMvcTest(ProductController.class)
class ProductControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ProductService productService;

    @Test
    void getById_ReturnsProduct() throws Exception {
        ProductDto product = new ProductDto(1L, "Recliner", new BigDecimal("999.99"),
                "furniture", LocalDateTime.now());
        when(productService.findById(1L)).thenReturn(product);

        mockMvc.perform(get("/api/v1/products/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Recliner"))
                .andExpect(jsonPath("$.price").value(999.99));
    }

    @Test
    void getById_NotFound_Returns404() throws Exception {
        when(productService.findById(99L))
                .thenThrow(new EntityNotFoundException("Product not found: 99"));

        mockMvc.perform(get("/api/v1/products/99"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Resource Not Found"));
    }

    @Test
    void create_ValidRequest_Returns201() throws Exception {
        CreateProductRequest request = new CreateProductRequest(
                "Sofa", new BigDecimal("1499.99"), "furniture");
        ProductDto created = new ProductDto(2L, "Sofa", new BigDecimal("1499.99"),
                "furniture", LocalDateTime.now());
        when(productService.create(any())).thenReturn(created);

        mockMvc.perform(post("/api/v1/products")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                            {"name": "Sofa", "price": 1499.99, "category": "furniture"}
                            """))
                .andExpect(status().isCreated())
                .andExpect(header().exists("Location"))
                .andExpect(jsonPath("$.name").value("Sofa"));
    }

    @Test
    void create_InvalidRequest_Returns400() throws Exception {
        mockMvc.perform(post("/api/v1/products")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                            {"name": "", "price": -1, "category": ""}
                            """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Validation Error"));
    }
}
```

### Testing with Security

```java
@WebMvcTest(ProductController.class)
@Import(SecurityConfig.class)
class ProductControllerSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ProductService productService;

    @Test
    @WithMockUser(roles = "ADMIN")
    void delete_AsAdmin_Returns204() throws Exception {
        mockMvc.perform(delete("/api/v1/products/1"))
                .andExpect(status().isNoContent());
    }

    @Test
    void delete_Unauthenticated_Returns401() throws Exception {
        mockMvc.perform(delete("/api/v1/products/1"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(roles = "USER")
    void delete_AsUser_Returns403() throws Exception {
        mockMvc.perform(delete("/api/v1/products/1"))
                .andExpect(status().isForbidden());
    }
}
```

---

## 3. @DataJpaTest -- Repository Testing

`@DataJpaTest` loads JPA components: repositories, entities, `EntityManager`,
and an embedded database (H2 by default). Each test runs in a transaction
that is rolled back automatically.

### Basic Repository Test

```java
@DataJpaTest
class ProductRepositoryTest {

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private TestEntityManager entityManager;

    @Test
    void findBySlug_ExistingSlug_ReturnsProduct() {
        Product product = Product.builder()
                .name("La-Z-Boy Recliner")
                .slug("la-z-boy-recliner")
                .price(new BigDecimal("899.99"))
                .category("recliners")
                .build();
        entityManager.persistAndFlush(product);

        Optional<Product> found = productRepository.findBySlug("la-z-boy-recliner");

        assertThat(found).isPresent();
        assertThat(found.get().getName()).isEqualTo("La-Z-Boy Recliner");
    }

    @Test
    void findByCategoryAndPriceRange_ReturnsFilteredResults() {
        entityManager.persistAndFlush(Product.builder()
                .name("Budget Recliner").slug("budget").price(new BigDecimal("300"))
                .category("recliners").build());
        entityManager.persistAndFlush(Product.builder()
                .name("Premium Recliner").slug("premium").price(new BigDecimal("1500"))
                .category("recliners").build());
        entityManager.persistAndFlush(Product.builder()
                .name("Sofa").slug("sofa").price(new BigDecimal("800"))
                .category("sofas").build());

        Page<Product> results = productRepository.findByCategoryAndPriceRange(
                "recliners", new BigDecimal("200"), new BigDecimal("1000"),
                PageRequest.of(0, 10));

        assertThat(results.getContent()).hasSize(1);
        assertThat(results.getContent().get(0).getName()).isEqualTo("Budget Recliner");
    }
}
```

### Testing with Real Database (TestContainers)

```java
@DataJpaTest
@Testcontainers
@AutoConfigureTestDatabase(replace = Replace.NONE)
class ProductRepositoryPostgresTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
            .withDatabaseName("testdb")
            .withUsername("test")
            .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private ProductRepository productRepository;

    @Test
    void save_PersistsToPostgres() {
        Product product = Product.builder()
                .name("Test Product").slug("test-product")
                .price(new BigDecimal("99.99")).category("test").build();

        Product saved = productRepository.save(product);

        assertThat(saved.getId()).isNotNull();
    }
}
```

---

## 4. @SpringBootTest -- Integration Testing

Full context integration tests verify that all layers work together.
Use `@SpringBootTest` with `webEnvironment = RANDOM_PORT` for tests
that need the embedded server running.

### Full Stack Integration Test

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
class ProductIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
            .withDatabaseName("testdb");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private TestRestTemplate restTemplate;

    @Test
    void createAndRetrieveProduct() {
        // Create
        CreateProductRequest request = new CreateProductRequest(
                "Integration Test Sofa", new BigDecimal("799.99"), "sofas");
        ResponseEntity<ProductDto> createResponse = restTemplate.postForEntity(
                "/api/v1/products", request, ProductDto.class);

        assertThat(createResponse.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(createResponse.getBody()).isNotNull();
        Long productId = createResponse.getBody().id();

        // Retrieve
        ResponseEntity<ProductDto> getResponse = restTemplate.getForEntity(
                "/api/v1/products/" + productId, ProductDto.class);

        assertThat(getResponse.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(getResponse.getBody().name()).isEqualTo("Integration Test Sofa");
    }
}
```

---

## 5. TestContainers Patterns

### Shared Container for Test Suite

Reuse a single container across all tests in a class hierarchy to
avoid repeated container startup overhead.

```java
@Testcontainers
public abstract class AbstractIntegrationTest {

    @Container
    protected static final PostgreSQLContainer<?> POSTGRES =
            new PostgreSQLContainer<>("postgres:16")
                    .withDatabaseName("testdb")
                    .withUsername("test")
                    .withPassword("test");

    @Container
    protected static final GenericContainer<?> REDIS =
            new GenericContainer<>("redis:7-alpine")
                    .withExposedPorts(6379);

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
        registry.add("spring.data.redis.host", REDIS::getHost);
        registry.add("spring.data.redis.port", () -> REDIS.getMappedPort(6379));
    }
}
```

### Singleton Container Pattern

For even faster tests across multiple test classes, use a singleton
container that starts once for the entire test run.

```java
public abstract class SharedContainerTest {

    static final PostgreSQLContainer<?> POSTGRES;

    static {
        POSTGRES = new PostgreSQLContainer<>("postgres:16")
                .withDatabaseName("testdb");
        POSTGRES.start();  // Starts once, reused across all subclasses
    }

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }
}
```

---

## 6. MockMvc Patterns

### Common Request Patterns

```java
// GET with query params
mockMvc.perform(get("/api/v1/products")
        .param("page", "0")
        .param("size", "10")
        .param("sort", "price"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.content").isArray())
        .andExpect(jsonPath("$.totalElements").isNumber());

// POST with JSON body
mockMvc.perform(post("/api/v1/products")
        .contentType(MediaType.APPLICATION_JSON)
        .content(objectMapper.writeValueAsString(request)))
        .andExpect(status().isCreated());

// PUT with path variable and body
mockMvc.perform(put("/api/v1/products/{id}", 1L)
        .contentType(MediaType.APPLICATION_JSON)
        .content(objectMapper.writeValueAsString(updateRequest)))
        .andExpect(status().isOk());

// DELETE
mockMvc.perform(delete("/api/v1/products/{id}", 1L))
        .andExpect(status().isNoContent());

// With authentication header
mockMvc.perform(get("/api/v1/products")
        .header("Authorization", "Bearer " + jwtToken))
        .andExpect(status().isOk());
```

### Response Validation with JsonPath

```java
mockMvc.perform(get("/api/v1/products/1"))
        .andExpect(jsonPath("$.id").value(1))
        .andExpect(jsonPath("$.name").value("Recliner"))
        .andExpect(jsonPath("$.price").value(999.99))
        .andExpect(jsonPath("$.category").exists())
        .andExpect(jsonPath("$.internalField").doesNotExist())
        .andExpect(jsonPath("$.tags", hasSize(3)))
        .andExpect(jsonPath("$.tags[0]").value("furniture"));
```

---

## 7. Testing Best Practices

### Naming Convention

Use the pattern: `methodName_stateUnderTest_expectedBehavior`

```java
void findById_ExistingId_ReturnsProduct()
void findById_NonExistentId_ThrowsEntityNotFoundException()
void create_ValidRequest_ReturnsSavedProduct()
void create_DuplicateSlug_ThrowsDataIntegrityViolation()
```

### Test Data Builders

Use builder pattern for test data to keep tests readable and DRY.

```java
public class TestProductFactory {

    public static Product.ProductBuilder aProduct() {
        return Product.builder()
                .name("Default Product")
                .slug("default-product")
                .price(new BigDecimal("99.99"))
                .category("default");
    }

    public static CreateProductRequest.Builder aCreateRequest() {
        return CreateProductRequest.builder()
                .name("New Product")
                .price(new BigDecimal("199.99"))
                .category("furniture");
    }
}

// Usage in tests
Product product = TestProductFactory.aProduct()
        .name("Custom Name")
        .price(new BigDecimal("499.99"))
        .build();
```

### Assertion Libraries

Use AssertJ for fluent, readable assertions.

```java
// AssertJ -- preferred
assertThat(products).hasSize(3);
assertThat(products).extracting(Product::getName)
        .containsExactly("Chair", "Recliner", "Sofa");
assertThat(product.getPrice()).isGreaterThan(BigDecimal.ZERO);
assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);

// Asserting exceptions
assertThatThrownBy(() -> service.findById(99L))
        .isInstanceOf(EntityNotFoundException.class)
        .hasMessageContaining("Product not found");
```

### Test Configuration

```java
// application-test.yml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
  jpa:
    hibernate:
      ddl-auto: create-drop
    show-sql: true
  cache:
    type: none  # Disable caching in tests

logging:
  level:
    org.springframework.test: DEBUG
```

---

## 8. Common Anti-Patterns to Avoid

- **Loading full context for unit tests** -- Use `@WebMvcTest` or `@DataJpaTest` instead of `@SpringBootTest`
- **Testing framework behavior** -- Don't test that `@NotBlank` works; test your validation logic
- **Shared mutable test state** -- Each test must set up its own data; never depend on test ordering
- **Ignoring test performance** -- Use test slicing; a test suite that takes 10 minutes won't be run often
- **Not testing error paths** -- Test 404s, 400s, 409s, and 500s, not just happy paths
- **Mocking everything** -- Integration tests with TestContainers catch issues mocks hide
- **Using `@Transactional` in integration tests carelessly** -- It rolls back, which may hide commit-time errors

---

## 9. Test Organization

```
src/test/java/com/lazboy/products/
├── controller/
│   ├── ProductControllerTest.java      # @WebMvcTest
│   └── ProductControllerSecurityTest.java
├── service/
│   └── ProductServiceTest.java         # Unit test with Mockito
├── repository/
│   └── ProductRepositoryTest.java      # @DataJpaTest
├── integration/
│   └── ProductIntegrationTest.java     # @SpringBootTest + TestContainers
├── support/
│   ├── AbstractIntegrationTest.java    # Shared container base class
│   └── TestProductFactory.java         # Test data builders
└── resources/
    └── application-test.yml
```

---

*Spring Boot Testing Guide v1.0 | Aligned with lazboy-springboot-patterns skill*
