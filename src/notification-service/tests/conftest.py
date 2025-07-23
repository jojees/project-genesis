import pytest
import unittest.mock as mock
import os
import sys
import importlib

@pytest.fixture(autouse=True)
def reset_modules_for_tests():
    """
    Fixture to remove application modules and Pydantic-related modules from sys.modules
    before each test to ensure a completely clean slate for imports and patching.
    Also adds the project root to sys.path for module discovery.
    """
    original_sys_modules = sys.modules.copy()
    
    # List of modules specific to notification-service that might be imported
    # and need to be cleared for clean state between tests.
    modules_to_remove = [
        'notification_service',
        'notification_service.main',
        'notification_service.api',
        'notification_service.config',
        'notification_service.logger_config',
        'notification_service.postgres_service',
        'notification_service.rabbitmq_consumer',
        # FIX: Explicitly remove pika.adapters.asyncio_connection to ensure patching works
        'pika.adapters.asyncio_connection', 
        'pydantic',
        'pydantic_settings',
        'pydantic_core',
        'dotenv', # Also clear dotenv as it's being patched
    ]
    for module_name in modules_to_remove:
        if module_name in sys.modules:
            del sys.modules[module_name]

    print(f"\n--- Cleared {len(modules_to_remove)} application modules from sys.modules ---")

    # Add the parent directory of 'notification_service' to sys.path
    # This allows 'notification_service.config' to be imported correctly.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"--- Added {project_root} to sys.path ---")

    yield # Run the test

    # Remove the added path from sys.path
    if project_root in sys.path:
        sys.path.remove(project_root)
        print(f"--- Removed {project_root} from sys.path ---")

    sys.modules.clear()
    sys.modules.update(original_sys_modules)
    print("--- Restored original sys.modules ---")

# Removed the mock_env_vars fixture as environment variables will be managed
# directly within each test function for better isolation.
