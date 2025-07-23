import pytest
import unittest.mock as mock
import os
import importlib
from pydantic import ValidationError # Import ValidationError for testing
from pydantic_settings import BaseSettings # Import BaseSettings to patch its internal method
import dotenv # Import dotenv to correctly patch dotenv_values


# No longer relying on mock_env_vars fixture from conftest.py,
# managing env vars directly within each test.

def test_config_loads_all_env_vars_correctly():
    """
    Verify that the Config class correctly loads all environment variables
    and that their values match the mocked environment variables.
    """
    print("\n--- Test: Config Loads All Environment Variables Correctly ---")

    mock_env = {
        "RABBITMQ_HOST": "mock_rabbitmq_host",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USER": "mock_rabbitmq_user",
        "RABBITMQ_PASS": "mock_rabbitmq_pass",
        "RABBITMQ_ALERT_QUEUE": "mock_audit_alerts",
        "PG_HOST": "mock_pg_host",
        "PG_PORT": "5432",
        "PG_DB": "mock_pg_db",
        "PG_USER": "mock_pg_user",
        "PG_PASSWORD": "mock_pg_password",
        "SERVICE_NAME": "mock_notification_service",
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "API_HOST": "0.0.0.0",
        "API_PORT": "8000",
    }

    # Patch os.environ directly AND patch dotenv functions BEFORE importing the config module
    with mock.patch.dict(os.environ, mock_env, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None):
        
        # Import the config module *after* environment variables are mocked
        # and dotenv functions are patched.
        _config_module = importlib.import_module('notification_service.config')
        Config = _config_module.Config
        load_config = _config_module.load_config

        # Load the configuration
        config_instance = load_config()

        # Assert that each configuration field matches the mocked environment variable
        assert config_instance.rabbitmq_host == mock_env["RABBITMQ_HOST"]
        assert config_instance.rabbitmq_port == int(mock_env["RABBITMQ_PORT"])
        assert config_instance.rabbitmq_user == mock_env["RABBITMQ_USER"]
        assert config_instance.rabbitmq_pass == mock_env["RABBITMQ_PASS"]
        assert config_instance.rabbitmq_alert_queue == mock_env["RABBITMQ_ALERT_QUEUE"]

        assert config_instance.pg_host == mock_env["PG_HOST"]
        assert config_instance.pg_port == int(mock_env["PG_PORT"])
        assert config_instance.pg_db == mock_env["PG_DB"]
        assert config_instance.pg_user == mock_env["PG_USER"]
        assert config_instance.pg_password == mock_env["PG_PASSWORD"]

        assert config_instance.service_name == mock_env["SERVICE_NAME"]
        assert config_instance.environment == mock_env["ENVIRONMENT"]
        assert config_instance.log_level == mock_env["LOG_LEVEL"]

        assert config_instance.api_host == mock_env["API_HOST"]
        assert config_instance.api_port == int(mock_env["API_PORT"])

        print("Config loads all environment variables correctly verified.")


def test_config_parses_data_types_correctly():
    """
    Verify that the Config class correctly parses environment variables into
    their specified Python data types (e.g., int for ports, str for strings).
    """
    print("\n--- Test: Config Parses Data Types Correctly ---")

    # Define environment variables with string values that should be parsed
    mock_env = {
        "RABBITMQ_HOST": "another_host",
        "RABBITMQ_PORT": "5673", # String, should be parsed to int
        "RABBITMQ_USER": "another_user",
        "RABBITMQ_PASS": "another_pass",
        "RABBITMQ_ALERT_QUEUE": "another_queue",
        "PG_HOST": "another_pg_host",
        "PG_PORT": "5433", # String, should be parsed to int
        "PG_DB": "another_db",
        "PG_USER": "another_pg_user",
        "PG_PASSWORD": "another_pg_password",
        "SERVICE_NAME": "another-service",
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "DEBUG",
        "API_HOST": "127.0.0.1",
        "API_PORT": "8080", # String, should be parsed to int
    }

    # Patch os.environ directly AND patch dotenv functions BEFORE importing the config module
    with mock.patch.dict(os.environ, mock_env, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None):
            
        # Import the config module *after* environment variables are mocked
        _config_module = importlib.import_module('notification_service.config')
        Config = _config_module.Config
        load_config = _config_module.load_config

        config_instance = load_config()

        # Assert types and values
        assert isinstance(config_instance.rabbitmq_host, str)
        assert config_instance.rabbitmq_host == "another_host"

        assert isinstance(config_instance.rabbitmq_port, int)
        assert config_instance.rabbitmq_port == 5673

        assert isinstance(config_instance.pg_port, int)
        assert config_instance.pg_port == 5433

        assert isinstance(config_instance.api_port, int)
        assert config_instance.api_port == 8080

        assert isinstance(config_instance.log_level, str)
        assert config_instance.log_level == "DEBUG"

        print("Config parses data types correctly verified.")


def test_config_validation_for_invalid_types():
    """
    Verify that the Config class raises a ValidationError when environment variables
    are provided with values that cannot be parsed into their specified data types.
    """
    print("\n--- Test: Config Validation for Invalid Types ---")

    # Define environment variables with invalid types for integer fields
    mock_env = {
        "RABBITMQ_HOST": "host",
        "RABBITMQ_PORT": "not_an_int", # Invalid type
        "RABBITMQ_USER": "user",
        "RABBITMQ_PASS": "pass",
        "RABBITMQ_ALERT_QUEUE": "queue",
        "PG_HOST": "pg_host",
        "PG_PORT": "invalid_port", # Invalid type
        "PG_DB": "db",
        "PG_USER": "pg_user",
        "PG_PASSWORD": "pg_password",
        "SERVICE_NAME": "service",
        "ENVIRONMENT": "env",
        "LOG_LEVEL": "INFO",
        "API_HOST": "api_host",
        "API_PORT": "another_invalid_port", # Invalid type
    }

    # Patch os.environ directly AND patch dotenv functions BEFORE importing the config module
    with mock.patch.dict(os.environ, mock_env, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None):
            
        # Import the config module *after* environment variables are mocked
        _config_module = importlib.import_module('notification_service.config')
        load_config = _config_module.load_config

        # Expect a ValidationError to be raised
        with pytest.raises(ValidationError) as excinfo:
            load_config()

        # Assert that the error message contains expected parts
        # Updated assertion to match the more specific Pydantic error message
        assert "Input should be a valid integer, unable to parse string as an integer" in str(excinfo.value)
        # Assertions now check for lowercase field names as they appear in Pydantic's error message
        assert "rabbitmq_port" in str(excinfo.value)
        assert "pg_port" in str(excinfo.value)
        assert "api_port" in str(excinfo.value)

    print("Config validation for invalid types verified.")
