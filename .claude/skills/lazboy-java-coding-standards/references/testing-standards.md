# Java Testing Standards

Comprehensive guide to testing patterns for Spring Boot services using JUnit 5,
Mockito, AssertJ, and Testcontainers.

## 1. Test Naming Conventions

Use descriptive method names that express the behavior under test.

### Recommended Pattern: should_ExpectedBehavior_WhenCondition

```java
@Test
void shouldReturnUser_whenEmailExists() { ... }

@Test
void shouldThrowNotFoundException_whenUserIdInvalid() { ... }

@Test
void shouldSendWelcomeEmail_whenRegistrationSucceeds() { ... }

@Test
void shouldReturnEmptyList_whenNoOrdersExist() { ... }
```

### Alternative Pattern: methodName_condition_expectedResult

```java
@Test
void findByEmail_existingEmail_returnsUser() { ... }

@Test
void findByEmail_unknownEmail_throwsNotFoundException() { ... }
```

Pick one convention per project and enforce it consistently. Never use `test`
as a prefix -- JUnit 5 uses `@Test` annotation, not naming conventions.

## 2. Test Structure: Arrange-Act-Assert

Every test should have three distinct sections.

```java
@Test
void shouldCalculateOrderTotal_whenMultipleLineItems() {
    // Arrange
    var item1 = new LineItem("Widget", BigDecimal.valueOf(10.00), 2);
    var item2 = new LineItem("Gadget", BigDecimal.valueOf(25.00), 1);
    var order = new Order(List.of(item1, item2));

    // Act
    BigDecimal total = order.calculateTotal();

    // Assert
    assertThat(total).isEqualByComparingTo(BigDecimal.valueOf(45.00));
}
```

Keep each section focused:
- **Arrange:** Set up test data and dependencies. Use builder patterns for complex objects.
- **Act:** Call exactly one method or action.
- **Assert:** Verify the expected outcome. Prefer a single logical assertion.

## 3. JUnit 5 Annotations

### Core Annotations

```java
@ExtendWith(MockitoExtension.class)  // Enable Mockito
class OrderServiceTest {

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private PaymentService paymentService;

    @InjectMocks
    private OrderService orderService;

    @BeforeEach
    void setUp() {
        // Common setup if needed
    }

    @AfterEach
    void tearDown() {
        // Cleanup if needed
    }

    @Test
    void shouldPlaceOrder() { ... }

    @Test
    @Disabled("Pending API integration -- JIRA-1234")
    void shouldProcessRefund() { ... }

    @Test
    @Timeout(value = 5, unit = TimeUnit.SECONDS)
    void shouldCompleteWithinTimeout() { ... }
}
```

### Display Names

```java
@DisplayName("Order Service")
class OrderServiceTest {

    @Nested
    @DisplayName("when placing an order")
    class PlaceOrder {

        @Test
        @DisplayName("should create order with correct total")
        void shouldCreateOrder() { ... }

        @Test
        @DisplayName("should reject order when insufficient stock")
        void shouldRejectWhenNoStock() { ... }
    }

    @Nested
    @DisplayName("when cancelling an order")
    class CancelOrder {

        @Test
        @DisplayName("should refund payment")
        void shouldRefund() { ... }
    }
}
```

## 4. Parameterized Tests

### Value Sources

```java
@ParameterizedTest
@ValueSource(strings = {"", " ", "  \t  "})
void shouldRejectBlankNames(String name) {
    assertThatThrownBy(() -> new User(name, "user@test.com"))
        .isInstanceOf(IllegalArgumentException.class);
}

@ParameterizedTest
@NullAndEmptySource
@ValueSource(strings = {" ", "\t", "\n"})
void shouldRejectInvalidEmails(String email) {
    assertThat(EmailValidator.isValid(email)).isFalse();
}
```

### CSV Sources

```java
@ParameterizedTest
@CsvSource({
    "100, USD, $100.00",
    "1000, EUR, 1.000,00 EUR",
    "50, GBP, £50.00"
})
void shouldFormatCurrency(int amount, String currency, String expected) {
    var money = new Money(BigDecimal.valueOf(amount), Currency.getInstance(currency));
    assertThat(money.format()).isEqualTo(expected);
}

@ParameterizedTest
@CsvFileSource(resources = "/test-data/orders.csv", numLinesToSkip = 1)
void shouldCalculateShipping(String region, int weight, double expectedCost) {
    assertThat(ShippingCalculator.calculate(region, weight))
        .isCloseTo(expectedCost, within(0.01));
}
```

### Method Sources

```java
@ParameterizedTest
@MethodSource("validOrderProvider")
void shouldAcceptValidOrders(CreateOrderRequest request) {
    var result = orderService.validate(request);
    assertThat(result.isValid()).isTrue();
}

static Stream<Arguments> validOrderProvider() {
    return Stream.of(
        Arguments.of(new CreateOrderRequest(1L, 1, "123 Main St")),
        Arguments.of(new CreateOrderRequest(2L, 5, "456 Oak Ave")),
        Arguments.of(new CreateOrderRequest(3L, 100, "789 Pine Rd"))
    );
}
```

### Enum Sources

```java
@ParameterizedTest
@EnumSource(value = OrderStatus.class, names = {"ACTIVE", "PENDING"})
void shouldAllowCancellation(OrderStatus status) {
    var order = OrderFixture.withStatus(status);
    assertThat(order.canCancel()).isTrue();
}

@ParameterizedTest
@EnumSource(value = OrderStatus.class, mode = EnumSource.Mode.EXCLUDE, names = {"CANCELLED"})
void shouldHaveNonNullTimestamp(OrderStatus status) {
    var order = OrderFixture.withStatus(status);
    assertThat(order.getCreatedAt()).isNotNull();
}
```

## 5. AssertJ Best Practices

### Fluent Assertions

```java
// String assertions
assertThat(user.getName())
    .isNotBlank()
    .startsWith("John")
    .hasSize(8);

// Collection assertions
assertThat(orders)
    .hasSize(3)
    .extracting(Order::getStatus)
    .containsExactly(ACTIVE, PENDING, SHIPPED);

// Exception assertions
assertThatThrownBy(() -> service.findById(-1L))
    .isInstanceOf(NotFoundException.class)
    .hasMessageContaining("not found")
    .hasFieldOrPropertyWithValue("entityId", -1L);

// Optional assertions
assertThat(repository.findByEmail("test@test.com"))
    .isPresent()
    .get()
    .extracting(User::getName)
    .isEqualTo("Test User");

// Soft assertions -- report ALL failures, not just the first
SoftAssertions.assertSoftly(softly -> {
    softly.assertThat(response.getStatus()).isEqualTo(200);
    softly.assertThat(response.getBody()).isNotNull();
    softly.assertThat(response.getHeaders()).containsKey("Content-Type");
});
```

### Custom Assertions

```java
public class OrderAssert extends AbstractAssert<OrderAssert, Order> {
    protected OrderAssert(Order actual) {
        super(actual, OrderAssert.class);
    }

    public static OrderAssert assertThat(Order actual) {
        return new OrderAssert(actual);
    }

    public OrderAssert hasStatus(OrderStatus expected) {
        isNotNull();
        if (actual.getStatus() != expected) {
            failWithMessage("Expected status <%s> but was <%s>", expected, actual.getStatus());
        }
        return this;
    }

    public OrderAssert hasTotalGreaterThan(BigDecimal min) {
        isNotNull();
        if (actual.getTotal().compareTo(min) <= 0) {
            failWithMessage("Expected total > <%s> but was <%s>", min, actual.getTotal());
        }
        return this;
    }
}
```

## 6. Mockito Patterns

### Stubbing

```java
// Return value
when(repository.findById(1L)).thenReturn(Optional.of(order));

// Return different values on successive calls
when(idGenerator.next())
    .thenReturn(1L)
    .thenReturn(2L)
    .thenReturn(3L);

// Throw exception
when(paymentService.charge(any())).thenThrow(new PaymentException("Declined"));

// Answer with custom logic
when(repository.save(any(Order.class))).thenAnswer(invocation -> {
    Order order = invocation.getArgument(0);
    return new Order(42L, order.getProduct(), order.getQuantity(), order.getStatus());
});
```

### Verification

```java
// Verify method was called
verify(emailService).sendConfirmation(eq("user@test.com"), any(Order.class));

// Verify call count
verify(repository, times(1)).save(any());
verify(repository, never()).delete(any());
verify(auditLog, atLeastOnce()).log(anyString());

// Verify call order
InOrder inOrder = inOrder(repository, emailService);
inOrder.verify(repository).save(any());
inOrder.verify(emailService).sendConfirmation(anyString(), any());

// Capture arguments
ArgumentCaptor<Order> captor = ArgumentCaptor.forClass(Order.class);
verify(repository).save(captor.capture());
assertThat(captor.getValue().getStatus()).isEqualTo(OrderStatus.PENDING);
```

### Mockito Anti-Patterns

```java
// BAD: mocking value objects -- just use the real object
when(money.getAmount()).thenReturn(BigDecimal.TEN);  // Don't do this

// BAD: verifying getters
verify(order).getStatus();  // Don't verify queries, only commands

// BAD: excessive mocking -- test is brittle
when(repo.findById(1L)).thenReturn(Optional.of(order));
when(order.getId()).thenReturn(1L);
when(order.getStatus()).thenReturn(ACTIVE);
// This test tests the mocks, not the code

// GOOD: use real objects for data, mock only external dependencies
var order = new Order(1L, product, 2, OrderStatus.ACTIVE);
when(repo.findById(1L)).thenReturn(Optional.of(order));
```

## 7. Test Organization

### Test Class per Production Class

```
src/test/java/com/lazboy/app/
├── service/
│   ├── OrderServiceTest.java
│   ├── PaymentServiceTest.java
│   └── UserServiceTest.java
├── controller/
│   ├── OrderControllerTest.java
│   └── UserControllerTest.java
├── domain/
│   ├── MoneyTest.java
│   └── OrderTest.java
└── integration/
    ├── OrderIntegrationTest.java
    └── UserIntegrationTest.java
```

### Test Fixtures

```java
public class OrderFixture {
    public static Order activeOrder() {
        return new Order(1L, ProductFixture.widget(), 2, OrderStatus.ACTIVE);
    }

    public static Order pendingOrder() {
        return new Order(2L, ProductFixture.gadget(), 1, OrderStatus.PENDING);
    }

    public static CreateOrderRequest validRequest() {
        return new CreateOrderRequest(1L, 2, "123 Main St");
    }
}
```

### Builder Pattern for Test Data

```java
public class OrderBuilder {
    private Long id = 1L;
    private Product product = ProductFixture.widget();
    private int quantity = 1;
    private OrderStatus status = OrderStatus.ACTIVE;

    public static OrderBuilder anOrder() { return new OrderBuilder(); }

    public OrderBuilder withId(Long id) { this.id = id; return this; }
    public OrderBuilder withProduct(Product p) { this.product = p; return this; }
    public OrderBuilder withQuantity(int q) { this.quantity = q; return this; }
    public OrderBuilder withStatus(OrderStatus s) { this.status = s; return this; }

    public Order build() { return new Order(id, product, quantity, status); }
}

// Usage
var order = OrderBuilder.anOrder()
    .withQuantity(5)
    .withStatus(OrderStatus.SHIPPED)
    .build();
```

## 8. Integration Testing with Testcontainers

### PostgreSQL Container

```java
@SpringBootTest
@Testcontainers
class OrderIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15-alpine")
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
    private OrderService orderService;

    @Test
    void shouldPersistAndRetrieveOrder() {
        var request = new CreateOrderRequest(1L, 2, "123 Main St");
        var created = orderService.createOrder(request);

        var retrieved = orderService.findById(created.id());

        assertThat(retrieved.quantity()).isEqualTo(2);
        assertThat(retrieved.status()).isEqualTo(OrderStatus.PENDING);
    }
}
```

### Redis Container

```java
@Container
static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine")
    .withExposedPorts(6379);

@DynamicPropertySource
static void redisProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.data.redis.host", redis::getHost);
    registry.add("spring.data.redis.port", redis::getFirstMappedPort);
}
```

### Kafka Container

```java
@Container
static KafkaContainer kafka = new KafkaContainer(
    DockerImageName.parse("confluentinc/cp-kafka:7.5.0")
);

@DynamicPropertySource
static void kafkaProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
}
```

## 9. Spring Boot Test Slices

### WebMvcTest (Controller Layer)

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private OrderService orderService;

    @Test
    void shouldReturnOrder_whenGetById() throws Exception {
        var response = new OrderResponse(1L, "Widget", 2, BigDecimal.valueOf(20), OrderStatus.ACTIVE);
        when(orderService.findById(1L)).thenReturn(response);

        mockMvc.perform(get("/api/orders/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(1))
            .andExpect(jsonPath("$.productName").value("Widget"))
            .andExpect(jsonPath("$.status").value("ACTIVE"));
    }

    @Test
    void shouldReturn404_whenOrderNotFound() throws Exception {
        when(orderService.findById(99L)).thenThrow(new OrderNotFoundException(99L));

        mockMvc.perform(get("/api/orders/99"))
            .andExpect(status().isNotFound());
    }

    @Test
    void shouldReturn400_whenInvalidRequest() throws Exception {
        String invalidJson = """
            { "productId": null, "quantity": -1, "shippingAddress": "" }
            """;

        mockMvc.perform(post("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content(invalidJson))
            .andExpect(status().isBadRequest());
    }
}
```

### DataJpaTest (Repository Layer)

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class OrderRepositoryTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15-alpine");

    @DynamicPropertySource
    static void dbProps(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private OrderRepository orderRepository;

    @Autowired
    private TestEntityManager entityManager;

    @Test
    void shouldFindOrdersByStatus() {
        entityManager.persist(new Order(null, "Widget", 1, OrderStatus.ACTIVE));
        entityManager.persist(new Order(null, "Gadget", 2, OrderStatus.CANCELLED));
        entityManager.flush();

        List<Order> activeOrders = orderRepository.findByStatus(OrderStatus.ACTIVE);

        assertThat(activeOrders).hasSize(1);
        assertThat(activeOrders.get(0).getProductName()).isEqualTo("Widget");
    }
}
```

## 10. Testing Checklist

| Category | Check |
|----------|-------|
| Unit tests | Every public method in service classes is tested |
| Edge cases | Null inputs, empty collections, boundary values |
| Error paths | Exceptions are thrown with correct type and message |
| Naming | Tests describe behavior, not implementation |
| Independence | Tests do not depend on execution order |
| Speed | Unit tests complete in < 100ms each |
| Assertions | Use AssertJ, not JUnit assertEquals |
| Mocks | Only mock external dependencies, not value objects |
| Integration | Database and messaging tested with Testcontainers |
| Coverage | Aim for 80%+ line coverage on business logic |
