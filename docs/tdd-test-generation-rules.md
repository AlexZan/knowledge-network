# TDD Unit Test Generation Rules for AI Agents

Concise, actionable rules for generating Python pytest unit tests. Every line is a rule.

## 1. Unit Test Scope

**One Reason to Fail Rule:**
- Each test verifies ONE piece of functionality from ONE function/method
- Test should fail for exactly ONE reason (one logic path, one edge case, one error condition)
- If a test can fail because of bugs in multiple functions, it's not a unit test

**What's In Scope:**
- A single function/method's behavior
- A single logical responsibility (one input→output transformation)
- Testing one class is acceptable IF that class has a single responsibility

**What's Out of Scope:**
- Multiple functions collaborating (that's integration testing)
- End-to-end workflows across modules
- External systems (databases, APIs, file I/O) without mocks

**Example - GOOD:**
```python
def test_calculate_discount_returns_10_percent_for_members():
    result = calculate_discount(price=100, is_member=True)
    assert result == 10
```

**Example - BAD (tests too much):**
```python
def test_checkout_process():  # Tests: validation, calculation, database save, email send
    cart = ShoppingCart()
    cart.add_item("book", 20)
    order = cart.checkout(user)
    assert order.total == 20
    assert order.saved_to_db
    assert email_sent
```

## 2. Mocking in Python

### Core Rule: Patch Where Imported, Not Where Defined

**Wrong:**
```python
@patch('requests.get')  # Patches requests module, not where your code imported it
def test_fetch_data(mock_get):
    result = fetch_data()
```

**Right:**
```python
@patch('my_module.requests')  # Patches the name MY_MODULE uses
def test_fetch_data(mock_get):
    result = fetch_data()
```

**Rule:** If `my_module.py` contains `import requests`, patch `my_module.requests`, NOT `requests.get`.

**Inner Imports:**
```python
# my_module.py
def fetch():
    import requests  # Import inside function
    return requests.get(url)

# test_my_module.py
@patch('my_module.requests')  # Still patch where it's looked up
def test_fetch(mock_requests):
    ...
```

### When to Mock

**DO mock:**
- External services (HTTP, databases, file system)
- Slow operations (sleep, network calls)
- Non-deterministic functions (random, datetime.now)
- Dependencies you want to isolate from the unit under test

**DON'T mock:**
- Simple data structures (lists, dicts, dataclasses)
- Pure functions with no side effects
- Code under test itself
- Standard library basics (len, str, int) unless they have side effects

**Anti-pattern - Over-mocking:**
```python
# BAD: Mocking simple data
@patch('my_module.User')
def test_get_name(mock_user):
    mock_user.return_value.name = "Alice"
    # Now you're testing the mock, not real User behavior

# GOOD: Use real objects for simple cases
def test_get_name():
    user = User(name="Alice")
    assert user.get_display_name() == "Alice"
```

### Mock Signatures with autospec

**Always use autospec=True for class/function mocks:**
```python
@patch('my_module.requests.get', autospec=True)
def test_fetch(mock_get):
    mock_get.return_value.status_code = 200
    # Now mock enforces real signature of requests.get
```

**Why:** Without autospec, mocks accept any arguments and hide bugs.

### Mock Assertions

**Assert interactions, not just return values:**
```python
def test_send_notification_calls_api():
    with patch('my_module.requests.post') as mock_post:
        send_notification(user_id=123, message="Hello")
        mock_post.assert_called_once_with(
            'https://api.example.com/notify',
            json={'user_id': 123, 'message': 'Hello'}
        )
```

**Common mock assertions:**
- `mock.assert_called_once()`
- `mock.assert_called_with(arg1, arg2)`
- `mock.assert_not_called()`
- `mock.call_count == 2`

## 3. Test Isolation

**Every test must be independent:**
- No shared state between tests
- No test depends on another test running first
- No side effects that affect other tests

**Use tmp_path for file operations:**
```python
def test_save_file(tmp_path):
    file_path = tmp_path / "data.txt"
    save_data(file_path, "content")
    assert file_path.read_text() == "content"
    # tmp_path automatically cleaned up after test
```

**DON'T use real files:**
```python
# BAD: Relies on external file state
def test_load_data():
    data = load_data("/tmp/test.json")  # What if file doesn't exist?
    assert data['key'] == 'value'
```

**Fixtures for setup/teardown:**
```python
@pytest.fixture
def user():
    """Each test gets a fresh user instance"""
    return User(name="Test", email="test@example.com")

def test_user_name(user):
    assert user.name == "Test"

def test_user_email(user):
    assert user.email == "test@example.com"
```

**Function-scoped by default:** Each test function gets its own fixture instance.

## 4. Assertion Best Practices

### What to Assert

**DO assert:**
- Return values: `assert result == expected`
- State changes: `assert user.is_active == True`
- Side effects via mocks: `mock.assert_called_once()`
- Exceptions: `with pytest.raises(ValueError):`
- Object attributes: `assert order.status == "confirmed"`

**DON'T assert:**
- Implementation details (private methods, internal variables)
- External service responses (mock them instead)
- Complex objects when you only care about one field
- Mock internals beyond call verification

**Anti-pattern - Testing Implementation:**
```python
# BAD: Asserting on private internals
def test_process_data():
    processor = DataProcessor()
    processor.process(data)
    assert processor._internal_cache == {...}  # Private implementation detail

# GOOD: Test public behavior
def test_process_data():
    processor = DataProcessor()
    result = processor.process(data)
    assert result.status == "processed"
```

### One Assertion Per Test (Guideline)

**Aim for one logical assertion:**
```python
# GOOD
def test_user_creation_sets_name():
    user = User(name="Alice")
    assert user.name == "Alice"

def test_user_creation_sets_email():
    user = User(email="alice@example.com")
    assert user.email == "alice@example.com"
```

**Multiple assertions acceptable when testing ONE behavior:**
```python
# ACCEPTABLE: Multiple assertions about same operation
def test_user_to_dict_format():
    user = User(name="Alice", email="alice@example.com")
    result = user.to_dict()
    assert result['name'] == "Alice"
    assert result['email'] == "alice@example.com"
    assert 'password' not in result  # All about to_dict() behavior
```

**Use subtests for variations:**
```python
@pytest.mark.parametrize("input,expected", [
    (5, 25),
    (10, 100),
    (-3, 9),
])
def test_square(input, expected):
    assert square(input) == expected
```

### Testing Exceptions

```python
def test_divide_by_zero_raises_error():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_invalid_input_raises_with_message():
    with pytest.raises(ValueError, match="must be positive"):
        create_user(age=-5)
```

## 5. TDD Red Phase Specifics

### Valid Failing Tests

**All these are valid red-phase failures:**
- Import errors: `ModuleNotFoundError: No module named 'my_module'`
- Name errors: `NameError: name 'calculate_discount' is not defined`
- Attribute errors: `AttributeError: module 'my_module' has no attribute 'User'`
- Assertion failures: `AssertionError: assert 0 == 10`
- Type errors: `TypeError: calculate_discount() missing 1 required positional argument`

**The test defines the interface:**
```python
# This test fails with ImportError - VALID RED
def test_calculate_discount_for_members():
    from shop import calculate_discount  # Module doesn't exist yet
    result = calculate_discount(price=100, is_member=True)
    assert result == 10
```

**Red → Green → Refactor:**
1. **Red:** Write test that fails (import error, assertion, etc.)
2. **Green:** Write MINIMAL code to make test pass
3. **Refactor:** Clean up code while keeping tests green

### Predicting Failures

**Before running the test, know how it will fail:**
- "This will fail with ImportError because module doesn't exist"
- "This will fail with AssertionError: 0 == 10 because function returns 0"
- "This will fail with AttributeError because User class has no 'email' attribute"

**If failure is unexpected, STOP and investigate:**
- Wrong mock target?
- Typo in test?
- Misunderstanding of requirements?

## 6. Common AI Test Generation Mistakes

### Mistake 1: Inventing APIs

**DON'T invent methods that don't exist:**
```python
# BAD: Assumes methods exist without checking
def test_user_login():
    user = User()
    user.authenticate(password="secret")  # Method doesn't exist
    assert user.is_authenticated()  # Method doesn't exist
```

**DO test based on actual/planned interface:**
```python
# GOOD: Test the interface you're about to create
def test_user_login():
    user = User(username="alice", password_hash=hash("secret"))
    result = user.check_password("secret")  # Defined interface
    assert result is True
```

### Mistake 2: Wrong Mock Targets

**DON'T mock at definition site:**
```python
# BAD
@patch('requests.get')  # Wrong - not where my_module looks it up
def test_fetch_data(mock_get):
    result = fetch_data()
```

**DO mock where imported:**
```python
# GOOD
@patch('my_module.requests.get')  # Right - where my_module imported it
def test_fetch_data(mock_get):
    mock_get.return_value.json.return_value = {'data': 'test'}
    result = fetch_data()
```

### Mistake 3: Integration Tests Disguised as Unit Tests

**DON'T test multiple units without mocks:**
```python
# BAD: Tests 3 functions, database, and file I/O
def test_process_order():
    order = create_order(items)  # Function 1
    save_to_database(order)      # Function 2 + DB
    send_email(order)            # Function 3 + email service
    assert order.status == "processed"
```

**DO isolate the unit:**
```python
# GOOD: Tests only process_order, mocks dependencies
@patch('my_module.save_to_database')
@patch('my_module.send_email')
def test_process_order(mock_email, mock_db):
    order = Order(items=[...])
    result = process_order(order)
    assert result.status == "processed"
    mock_db.assert_called_once_with(order)
    mock_email.assert_called_once_with(order)
```

### Mistake 4: Asserting on LLM Output

**DON'T assert exact LLM responses:**
```python
# BAD: LLM output is non-deterministic
def test_generate_summary():
    result = generate_summary(text)
    assert result == "This article discusses AI and machine learning."  # Will fail randomly
```

**DO test structure/properties:**
```python
# GOOD: Test deterministic properties
def test_generate_summary():
    result = generate_summary(text)
    assert isinstance(result, str)
    assert len(result) > 0
    assert len(result) < 500  # Max length constraint
    # Or mock the LLM call:
    with patch('my_module.llm_client.generate') as mock_llm:
        mock_llm.return_value = "Mocked summary"
        result = generate_summary(text)
        assert result == "Mocked summary"
```

### Mistake 5: Excessive Setup (Mother Hen Anti-pattern)

**DON'T create massive setup:**
```python
# BAD: 50 lines of setup for one assertion
def test_user_name():
    db = Database()
    db.connect()
    db.create_tables()
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    email_service = EmailService()
    user_service = UserService(auth_service, email_service, user_repo)
    user = user_service.create_user(name="Alice", email="alice@example.com")
    # ... 40 more lines ...
    assert user.name == "Alice"
```

**DO use fixtures and focus:**
```python
# GOOD: Minimal setup, fixtures for reuse
@pytest.fixture
def user_service():
    return UserService(auth=Mock(), email=Mock(), repo=Mock())

def test_user_creation_sets_name(user_service):
    user = user_service.create_user(name="Alice", email="alice@example.com")
    assert user.name == "Alice"
```

### Mistake 6: Testing Too Much at Once (Free Ride Anti-pattern)

**DON'T piggyback multiple assertions:**
```python
# BAD: Testing 4 different behaviors in one test
def test_user():
    user = User(name="Alice", email="alice@example.com", age=30)
    assert user.name == "Alice"  # Test 1
    assert user.email == "alice@example.com"  # Test 2
    assert user.is_adult() == True  # Test 3
    assert user.to_dict()['age'] == 30  # Test 4
```

**DO separate concerns:**
```python
# GOOD: One behavior per test
def test_user_name():
    user = User(name="Alice")
    assert user.name == "Alice"

def test_user_is_adult():
    user = User(age=30)
    assert user.is_adult() is True

def test_user_to_dict_includes_age():
    user = User(age=30)
    assert user.to_dict()['age'] == 30
```

### Mistake 7: Cryptic Names and Poor Readability

**DON'T use generic names:**
```python
# BAD
def test_func():
    result_obj = my_func(data_val)
    assert result_obj == expected_val
```

**DO use descriptive names:**
```python
# GOOD
def test_calculate_discount_returns_10_percent_for_members():
    member_discount = calculate_discount(price=100, is_member=True)
    assert member_discount == 10
```

**Test naming pattern:** `test_<function>_<scenario>_<expected_result>`

### Mistake 8: Not Using Parametrize for Variations

**DON'T duplicate tests:**
```python
# BAD: Copy-paste for each case
def test_square_positive():
    assert square(5) == 25

def test_square_negative():
    assert square(-3) == 9

def test_square_zero():
    assert square(0) == 0
```

**DO parametrize:**
```python
# GOOD
@pytest.mark.parametrize("input,expected", [
    (5, 25),
    (-3, 9),
    (0, 0),
])
def test_square(input, expected):
    assert square(input) == expected
```

## 7. Checklist for Every Test

Before generating a test, verify:

- [ ] Tests ONE function/method
- [ ] Has ONE reason to fail
- [ ] Mocks external dependencies (if any)
- [ ] Uses `tmp_path` for file operations
- [ ] Patches at import location, not definition
- [ ] Asserts on behavior, not implementation
- [ ] Uses descriptive name: `test_<what>_<scenario>_<outcome>`
- [ ] Independent (no shared state with other tests)
- [ ] Would fail first (red phase) then pass (green phase)
- [ ] Uses `autospec=True` for mocks of real objects
- [ ] No invented methods/attributes
- [ ] Minimal setup (use fixtures if needed)

## 8. Quick Reference: Test Structure

```python
# Standard AAA pattern
def test_function_name_scenario_expected():
    # ARRANGE: Set up test data and mocks
    input_data = {...}
    expected_output = {...}

    # ACT: Call the function under test
    result = function_under_test(input_data)

    # ASSERT: Verify the result
    assert result == expected_output
```

```python
# With mocking
@patch('module.dependency', autospec=True)
def test_function_with_dependency(mock_dependency):
    # ARRANGE
    mock_dependency.return_value = "mocked_result"
    input_data = "test"

    # ACT
    result = function_that_uses_dependency(input_data)

    # ASSERT
    assert result == "expected"
    mock_dependency.assert_called_once_with(input_data)
```

```python
# With fixtures
@pytest.fixture
def sample_user():
    return User(name="Alice", email="alice@example.com")

def test_user_display_name(sample_user):
    assert sample_user.get_display_name() == "Alice"
```

## 9. Red Phase Workflow

1. **Write the test first** - before any implementation exists
2. **Run the test** - it MUST fail
3. **Verify the failure** - check it fails for the RIGHT reason:
   - ImportError/NameError: Good - interface doesn't exist yet
   - AttributeError: Good - method doesn't exist yet
   - AssertionError: Good - logic returns wrong value
   - Unexpected error: BAD - fix the test
4. **Write minimal code** to make test pass
5. **Run test again** - it MUST pass
6. **Refactor** if needed (keep tests green)

## 10. When NOT to Use Mocks

**Simple data transformations:**
```python
# DON'T mock pure functions
def test_format_name():
    # No need to mock str.upper() or string operations
    result = format_name("alice")
    assert result == "Alice"
```

**Value objects:**
```python
# DON'T mock simple objects
def test_point_distance():
    p1 = Point(0, 0)  # Real object, not mocked
    p2 = Point(3, 4)  # Real object, not mocked
    assert calculate_distance(p1, p2) == 5.0
```

**Use real objects for:**
- Immutable data structures
- Simple calculations
- No side effects
- Fast execution
- Deterministic behavior

**Use mocks for:**
- Network calls (requests, API clients)
- Database operations (sqlalchemy, psycopg2)
- File system (open, pathlib operations beyond tmp_path)
- Time/randomness (datetime.now, random.random)
- External services (email, payment processors)

---

**Sources:**
- Martin Fowler: [Unit Test](https://martinfowler.com/bliki/UnitTest.html), [Test Shapes](https://martinfowler.com/articles/2021-test-shapes.html)
- Python docs: [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- pytest docs: [tmp_path](https://docs.pytest.org/en/stable/how-to/tmp_path.html), [assertions](https://docs.pytest.org/en/stable/how-to/assert.html), [monkeypatch](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
- Real Python: [Mock Library](https://realpython.com/python-mock-library/)
- Testing anti-patterns: [Unit Testing Anti-Patterns](https://www.yegor256.com/2018/12/11/unit-testing-anti-patterns.html)
- TDD fundamentals: [TDD MOOC](https://tdd.mooc.fi/1-tdd/), [Clean Coder TDD](http://blog.cleancoder.com/uncle-bob/2014/12/17/TheCyclesOfTDD.html)
- AI test generation: [Why AI Tests Fall Short](https://shekhar14.medium.com/unmasking-the-flaws-why-ai-generated-unit-tests-fall-short-in-real-codebases-71e394581a8e)
