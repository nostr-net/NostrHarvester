import json
from pathlib import Path
from typing import List

from pydantic.v1 import BaseSettings, Field, root_validator

import logging
from pydantic.v1 import ValidationError

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and optional config file.
    Hierarchical configuration precedence: environment variables > config file > defaults.
    """
    # Database settings
    pg_database: str = Field("nostr", env="PGDATABASE")
    pg_user: str = Field("nostr", env="PGUSER")
    pg_password: str = Field("nostr", env="PGPASSWORD")
    pg_host: str = Field("db", env="PGHOST")
    pg_port: int = Field(5432, env="PGPORT")

    # Feature toggles
    health_enabled: bool = Field(True, env="HEALTH_ENABLED")
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")

    # Indexer relay configuration file path
    relay_config_path: str = Field("config.json", env="RELAY_CONFIG_PATH")

    # General application JSON config file (hierarchical overrides)
    app_config_path: str = Field("config.json", env="APP_CONFIG_PATH")

    # Configuration hot-reloading and dynamic updates
    config_hot_reload_enabled: bool = Field(False, env="CONFIG_HOT_RELOAD_ENABLED")
    config_hot_reload_debounce_seconds: float = Field(
        1.0, env="CONFIG_HOT_RELOAD_DEBOUNCE_SECONDS"
    )

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # Event processing batching & worker pools
    event_batch_size: int = Field(100, env="EVENT_BATCH_SIZE")
    event_batch_interval: float = Field(1.0, env="EVENT_BATCH_INTERVAL")
    worker_pool_size: int = Field(4, env="WORKER_POOL_SIZE")

    # Circuit breaker settings for relay management
    circuit_breaker_failure_threshold: int = Field(
        5, env="CIRCUIT_BREAKER_FAILURE_THRESHOLD"
    )
    circuit_breaker_recovery_timeout: int = Field(
        60, env="CIRCUIT_BREAKER_RECOVERY_TIMEOUT"
    )

    # Security & rate limiting
    rate_limit_enabled: bool = Field(False, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(
        60, env="RATE_LIMIT_REQUESTS_PER_MINUTE"
    )

    # API query limits
    max_event_query_limit: int = Field(500, env="MAX_EVENT_QUERY_LIMIT")

    # Caching for expensive queries
    cache_enabled: bool = Field(False, env="CACHE_ENABLED")
    cache_ttl_seconds: int = Field(60, env="CACHE_TTL_SECONDS")
    cache_maxsize: int = Field(128, env="CACHE_MAXSIZE")

    # Advanced query performance: materialized views
    use_materialized_views: bool = Field(
        False, env="USE_MATERIALIZED_VIEWS"
    )
    matview_refresh_interval_seconds: int = Field(
        0, env="MATVIEW_REFRESH_INTERVAL_SECONDS"
    )

    # Database connection pooling settings
    pool_min_size: int = Field(1, env="PG_POOL_MIN_SIZE")
    pool_max_size: int = Field(10, env="PG_POOL_MAX_SIZE")

    # Extended observability: Prometheus metrics server for the indexer
    metrics_server_enabled: bool = Field(False, env="METRICS_SERVER_ENABLED")
    metrics_server_port: int = Field(8000, env="METRICS_SERVER_PORT")
    metrics_refresh_interval_seconds: float = Field(
        5.0, env="METRICS_REFRESH_INTERVAL_SECONDS"
    )

    # Security hardening settings
    request_max_size_bytes: int = Field(0, env="REQUEST_MAX_SIZE_BYTES")
    max_query_length: int = Field(500, env="MAX_QUERY_LENGTH")
    api_auth_enabled: bool = Field(False, env="API_AUTH_ENABLED")
    api_auth_token: str = Field("", env="API_AUTH_TOKEN")


    @root_validator(pre=True)
    def load_config_file(cls, values):
        # Merge in JSON config from app_config_path (env overrides > file > defaults)
        path = values.get("app_config_path") or cls.__fields__["app_config_path"].get_default()
        cfg_path = Path(path)
        if cfg_path.is_file():
            try:
                data = json.loads(cfg_path.read_text())
            except Exception:
                data = {}
            # Merge file values, do not override environment variables
            for k, v in data.items():
                if k in cls.__fields__ and values.get(k) is None:
                    values[k] = v
        return values


settings = Settings()

def reload_settings() -> None:
    """
    Reload configuration from environment variables and config file.
    On failure, logs an error and retains existing settings.
    """
    global settings
    try:
        new_settings = Settings()
    except ValidationError as e:
        logger.error(f"Error reloading configuration: {e}")
        return
    settings = new_settings