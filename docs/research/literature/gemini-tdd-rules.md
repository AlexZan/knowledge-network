# Gemini's TDD Unit Test Rules (for comparison)

Source: Gemini 3 Pro, 2026-02-08

### **Ruleset: TDD & Unit Testing Best Practices (Python/pytest)**

#### **1. Unit Test Scope & Anatomy**

*   **Rule: Test Behavior, Not Implementation**
    *   Focus on what the code *does* (public API), not *how* it does it.
    *   Example:
        ```python
        # BAD: Testing internal state or private methods
        def test_parser_internals():
            p = Parser()
            assert p._current_line == 0  # Private access

        # GOOD: Testing public behavior
        def test_parser_initial_state():
            p = Parser()
            assert p.is_empty() is True
        ```

*   **Rule: One Logical Concept Per Test**
    *   A test should verify a single behavior or path.
    *   Example:
        ```python
        # BAD: Testing happy path and error in one
        def test_calculation():
            assert add(2, 2) == 4
            with pytest.raises(TypeError):
                add("2", 2)

        # GOOD: Split into atomic tests
        def test_add_integers():
            assert add(2, 2) == 4

        def test_add_raises_on_string():
            with pytest.raises(TypeError):
                add("2", 2)
        ```

*   **Rule: Arrange, Act, Assert (AAA)**
    *   Structure tests clearly: Setup data, execute function, verify result.
    *   Keep the 'Act' phase to a single line/call if possible.

#### **2. Python Mocking Best Practices**

*   **Rule: Patch Where Imported, Not Where Defined**
    *   Patch the name *used* in the module under test.
    *   Example:
        ```python
        # src/service.py
        from src.api import Client
        def do_work():
            c = Client()
            return c.get_data()

        # tests/test_service.py
        # BAD: Patching the definition (has no effect on service.py's reference)
        @patch('src.api.Client')

        # GOOD: Patching the reference in the module under test
        @patch('src.service.Client')
        def test_do_work(mock_client_cls):
            ...
        ```

*   **Rule: Use `autospec=True`**
    *   Prevents mocks from accepting calls that the real object wouldn't.
    *   Example: `m = MagicMock(spec=RealClass)` or `@patch('...', autospec=True)`.

*   **Rule: Do Not Mock Value Objects / DTOs**
    *   If an object is just data (dataclass, pydantic model), use a real instance.

#### **3. Test Isolation & State**

*   **Rule: Independent Tests** — No test relies on execution order or state from another.
*   **Rule: Use `tmp_path` for File I/O** — Never write to actual filesystem or hardcoded paths.
*   **Rule: Avoid `global` State Mutation** — Use `monkeypatch` fixture for env vars, sys.modules.

#### **4. Assertion Best Practices**

*   **Rule: Assert on Return Values or State Changes** — Primary verification target.
*   **Rule: Do Not Assert on External Service Responses** — Mock the network layer, assert on handling.
*   **Rule: Use Specialized Assertions** — `pytest.approx` for floats, `items() <=` for partial dicts.

#### **5. TDD Red Phase Guidelines**

*   **Rule: The First Failure is `ImportError`** — Valid red state when module doesn't exist yet.
*   **Rule: Fail for the Right Reason** — SyntaxError or misconfiguration is not a valid Red.
*   **Rule: Minimal Implementation** — Hardcoding return values is acceptable for first pass.

#### **6. Common AI/LLM Generation Mistakes**

*   **Rule: Do Not Hallucinate Libraries** — Check deps, stick to stdlib and explicit dependencies.
*   **Rule: Do Not Invent APIs** — Don't call methods that don't exist in the codebase.
*   **Rule: Do Not Test the Library** — Don't verify json.loads works. Test YOUR usage of it.
*   **Rule: Asserting on Deterministic Output** — Mock LLM response. Assert your code processes it.
*   **Rule: Over-Mocking** — Only mock: Network, Disk, Slow things, Non-deterministic things.

#### **7. Complete TDD Cycle Example**

Step 1 (Red): Import function that doesn't exist → ImportError
Step 2 (Green): Write minimal code to pass
Step 3 (Refactor): Clean up, keep tests green
Step 4 (Red): Add edge case test
Step 5 (Green): Handle edge case
