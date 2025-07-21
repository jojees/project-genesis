## Lessons Learned: Improving Code for Easier Testing

To avoid future complications and make writing unit tests significantly easier, consider implementing the following practices in your application and test code:

### Application Design Principles (Making Code Inherently More Testable)

* [ ] **Implement Dependency Injection (DI) / Inversion of Control (IoC):**

  * **Action:** For new classes/functions, pass their dependencies (e.g., `pika` library, `config` object, `health_manager` instance, `logger` instance) as arguments to their constructors or functions, rather than importing and instantiating them directly within the module.

  * **Benefit:** Allows easy substitution of real dependencies with mocks in tests.

* [ ] **Minimize Global/Module-Level Mutable State:**

  * **Action:** Avoid using `global` keywords for variables that change state (like `connection`, `consumer_channel`, `publisher_channel`). Encapsulate mutable state within class instances.

  * **Benefit:** Reduces "state bleed" between tests, making tests more isolated and reliable.

* [ ] **Centralize and Explicitly Load Configuration:**

  * **Action:** Create a dedicated function (e.g., `config.load_settings()`) that reads environment variables or configuration files. Call this function once at application startup to get all settings.

  * **Benefit:** Allows mocking the configuration loading function to return controlled settings in tests, bypassing `os.environ` and `.env` file complexities.

### Testing Best Practices (Making Test Code Easier to Write and Maintain)

* [ ] **Mock at the Seam (Point of Interaction):**

  * **Action:** When writing tests, identify exactly where your code interacts with an external dependency (e.g., `rabbitmq_consumer_service` calls `pika.BlockingConnection`). Patch the dependency at that specific import path.

  * **Benefit:** Ensures your mock is used consistently, reduces the need for complex `sys.modules` manipulation, and makes tests more resilient to internal changes in the dependency.

* [ ] **Prioritize Test Isolation:**

  * **Action:** Ensure each test function is completely independent. If tests interfere with each other, it's a sign of state bleed. Use fixtures to set up and tear down a clean environment for *every* test.

  * **Benefit:** Leads to a stable and reliable test suite where failures are easy to diagnose.

* [ ] **Leverage Pytest Fixtures for Setup/Teardown:**

  * **Action:** For common setup tasks (like clearing Prometheus registries or setting up mock objects), use `pytest.fixture` with `autouse=True` where appropriate, or pass them explicitly.

  * **Benefit:** Centralizes setup logic, reduces boilerplate in individual test functions, and ensures consistent test environments.

* [ ] **Avoid `importlib.reload()` and `sys.modules` Manipulation (Unless Absolutely Necessary):**

  * **Action:** If your application code follows Dependency Injection, you generally won't need to force module reloads or directly manipulate `sys.modules` in tests. Reserve these advanced techniques only for legacy code or very specific scenarios where refactoring isn't feasible.

  * **Benefit:** Simplifies test code significantly and reduces the chances of subtle state-related bugs.