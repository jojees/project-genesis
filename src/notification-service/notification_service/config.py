# notification_service/notification_service/config.py
import os
from pydantic import Field # Assuming you're using pydantic for Config
from pydantic_settings import BaseSettings, SettingsConfigDict

# Assuming your Config class looks something like this:
class Config(BaseSettings): # Or just a regular class if not using pydantic-settings
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # RabbitMQ Configuration
    rabbitmq_host: str = Field(..., env="RABBITMQ_HOST")
    rabbitmq_port: int = Field(..., env="RABBITMQ_PORT")
    rabbitmq_user: str = Field(..., env="RABBITMQ_USER")
    rabbitmq_pass: str = Field(..., env="RABBITMQ_PASS")
    rabbitmq_alert_queue: str = Field(..., env="RABBITMQ_ALERT_QUEUE")

    # PostgreSQL Configuration
    pg_host: str = Field(..., env="PG_HOST")
    pg_port: int = Field(..., env="PG_PORT")
    pg_db: str = Field(..., env="PG_DB")
    pg_user: str = Field(..., env="PG_USER")
    pg_password: str = Field(..., env="PG_PASSWORD")

    # Service specific
    service_name: str = Field(..., env="SERVICE_NAME")
    environment: str = Field(..., env="ENVIRONMENT")

    # Logging level
    log_level: str = Field(..., env="LOG_LEVEL")

    # --- NEW: API Configuration for Notification Service itself ---
    api_host: str = Field(..., env="API_HOST")
    api_port: int = Field(..., env="API_PORT")

def load_config() -> Config:
    return Config()