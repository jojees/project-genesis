import pytest
import unittest.mock as mock
import os
import importlib

# Define a dictionary of mock environment variables that are ACTUALLY loaded from os.environ
MOCK_ENV_VARS_LOADED = {
    "RABBITMQ_HOST": "mock-rabbitmq-env",
    "RABBITMQ_PORT": "5673",
    "RABBITMQ_USER": "mock_env_user",
    "RABBITMQ_PASS": "mock_env_pass",
    "RABBITMQ_QUEUE": "mock_audit_events_env",
    "APP_PORT": "5002",
    "PROMETHEUS_PORT": "8002",
    "RABBITMQ_ALERT_QUEUE": "mock_audit_alerts_env",
    "REDIS_HOST": "mock-redis-env",
    "REDIS_PORT": "6380", # Added REDIS_PORT based on config.py
}

def test_config_loads_from_env_vars():
    """
    Verify that the config module correctly loads specific values from mocked environment variables.
    """
    # Use patch.dict to temporarily set environment variables for the test.
    # clear=True ensures only our mocked variables are present, preventing
    # interference from the actual system environment or .env file loading.
    with mock.patch.dict(os.environ, MOCK_ENV_VARS_LOADED, clear=True):
        # Import or reload the config module *after* patching os.environ.
        # This ensures it reads the newly mocked environment variables.
        import audit_analysis.config as config
        importlib.reload(config)

        print("\n--- Test: Config Loads from Specific Environment Variables ---")

        # Assert that each config variable loaded from environment matches its mocked value
        assert config.RABBITMQ_HOST == MOCK_ENV_VARS_LOADED["RABBITMQ_HOST"]
        assert config.RABBITMQ_PORT == int(MOCK_ENV_VARS_LOADED["RABBITMQ_PORT"])
        assert config.RABBITMQ_USER == MOCK_ENV_VARS_LOADED["RABBITMQ_USER"]
        assert config.RABBITMQ_PASS == MOCK_ENV_VARS_LOADED["RABBITMQ_PASS"]
        assert config.RABBITMQ_QUEUE == MOCK_ENV_VARS_LOADED["RABBITMQ_QUEUE"]
        assert config.APP_PORT == int(MOCK_ENV_VARS_LOADED["APP_PORT"])
        assert config.PROMETHEUS_PORT == int(MOCK_ENV_VARS_LOADED["PROMETHEUS_PORT"])
        assert config.RABBITMQ_ALERT_QUEUE == MOCK_ENV_VARS_LOADED["RABBITMQ_ALERT_QUEUE"]
        assert config.REDIS_HOST == MOCK_ENV_VARS_LOADED["REDIS_HOST"]
        assert config.REDIS_PORT == int(MOCK_ENV_VARS_LOADED["REDIS_PORT"])

        print("All environment-loaded config variables match mocked values.")


# Define expected default values from config.py
EXPECTED_DEFAULT_CONFIG = {
    "RABBITMQ_HOST": "rabbitmq-service",
    "RABBITMQ_PORT": 5672,
    "RABBITMQ_USER": "jdevlab",
    "RABBITMQ_PASS": "jdevlab",
    "RABBITMQ_QUEUE": "audit_events",
    "APP_PORT": 5001,
    "PROMETHEUS_PORT": 8001,
    "RABBITMQ_ALERT_QUEUE": "audit_alerts",
    "REDIS_HOST": "redis-service",
    "REDIS_PORT": 6379,
    "FAILED_LOGIN_WINDOW_SECONDS": 60,
    "FAILED_LOGIN_THRESHOLD": 3,
    "SENSITIVE_FILES": ["/etc/sudoers", "/root/.ssh/authorized_keys", "/etc/shadow", "/etc/passwd"],
}

def test_config_uses_default_values():
    """
    Verify that the config module correctly uses default values when
    environment variables are not set.
    """
    # Patch os.environ with an empty dictionary, clearing all existing
    # environment variables. This ensures that os.environ.get() will fall back
    # to its default arguments or the hardcoded values in config.py.
    with mock.patch.dict(os.environ, {}, clear=True):
        # Import or reload the config module *after* patching os.environ.
        # This is crucial to ensure it reads from the now-empty environment.
        import audit_analysis.config as config
        importlib.reload(config)

        print("\n--- Test: Config Uses Default Values ---")

        # Assert that each config variable matches its expected default value
        assert config.RABBITMQ_HOST == EXPECTED_DEFAULT_CONFIG["RABBITMQ_HOST"]
        assert config.RABBITMQ_PORT == EXPECTED_DEFAULT_CONFIG["RABBITMQ_PORT"]
        assert config.RABBITMQ_USER == EXPECTED_DEFAULT_CONFIG["RABBITMQ_USER"]
        assert config.RABBITMQ_PASS == EXPECTED_DEFAULT_CONFIG["RABBITMQ_PASS"]
        assert config.RABBITMQ_QUEUE == EXPECTED_DEFAULT_CONFIG["RABBITMQ_QUEUE"]
        assert config.APP_PORT == EXPECTED_DEFAULT_CONFIG["APP_PORT"]
        assert config.PROMETHEUS_PORT == EXPECTED_DEFAULT_CONFIG["PROMETHEUS_PORT"]
        assert config.RABBITMQ_ALERT_QUEUE == EXPECTED_DEFAULT_CONFIG["RABBITMQ_ALERT_QUEUE"]
        assert config.REDIS_HOST == EXPECTED_DEFAULT_CONFIG["REDIS_HOST"]
        assert config.REDIS_PORT == EXPECTED_DEFAULT_CONFIG["REDIS_PORT"]
        assert config.FAILED_LOGIN_WINDOW_SECONDS == EXPECTED_DEFAULT_CONFIG["FAILED_LOGIN_WINDOW_SECONDS"]
        assert config.FAILED_LOGIN_THRESHOLD == EXPECTED_DEFAULT_CONFIG["FAILED_LOGIN_THRESHOLD"]
        assert config.SENSITIVE_FILES == EXPECTED_DEFAULT_CONFIG["SENSITIVE_FILES"]

        print("All config variables correctly loaded default or hardcoded values.")


def test_sensitive_files_list():
    """
    Verify that the SENSITIVE_FILES list in config.py contains the expected hardcoded paths.
    """
    # No need to mock os.environ as SENSITIVE_FILES is hardcoded.
    # Just reload to ensure we get the module's state directly.
    import audit_analysis.config as config
    importlib.reload(config)

    print("\n--- Test: Sensitive Files List Content ---")

    # Assert that SENSITIVE_FILES is a list
    assert isinstance(config.SENSITIVE_FILES, list)

    # Assert that the list contains the exact expected paths
    assert config.SENSITIVE_FILES == [
        "/etc/sudoers",
        "/root/.ssh/authorized_keys",
        "/etc/shadow",
        "/etc/passwd"
    ]
    print("SENSITIVE_FILES list content is as expected.")


def test_failed_login_rule_parameters():
    """
    Verify that the FAILED_LOGIN_WINDOW_SECONDS and FAILED_LOGIN_THRESHOLD
    parameters in config.py contain the expected hardcoded values.
    """
    # No need to mock os.environ as these are hardcoded.
    import audit_analysis.config as config
    importlib.reload(config)

    print("\n--- Test: Failed Login Rule Parameters ---")

    # Assert values and types
    assert config.FAILED_LOGIN_WINDOW_SECONDS == EXPECTED_DEFAULT_CONFIG["FAILED_LOGIN_WINDOW_SECONDS"]
    assert isinstance(config.FAILED_LOGIN_WINDOW_SECONDS, int)

    assert config.FAILED_LOGIN_THRESHOLD == EXPECTED_DEFAULT_CONFIG["FAILED_LOGIN_THRESHOLD"]
    assert isinstance(config.FAILED_LOGIN_THRESHOLD, int)

    print("Failed login rule parameters are as expected.")