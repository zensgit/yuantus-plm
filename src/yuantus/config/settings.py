from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="YUANTUS_",
        env_file=".env",
        extra="ignore",
    )

    # Runtime
    ENVIRONMENT: str = Field(default="dev", description="Environment name")
    HOST: str = Field(default="0.0.0.0", description="Bind host")
    PORT: int = Field(default=7910, description="Bind port")

    # Tenancy
    # single: one database for all tenants (default)
    # db-per-tenant: one database/schema per tenant (dev-friendly for SaaS)
    # db-per-tenant-org: one database per (tenant, org) for strong isolation
    TENANCY_MODE: str = Field(
        default="single", description="single|db-per-tenant|db-per-tenant-org"
    )
    DATABASE_URL_TEMPLATE: str = Field(
        default="",
        description="Optional template for db-per-tenant/org, e.g. sqlite:///yuantus_dev__{tenant_id}__{org_id}.db",
    )

    # Multi-tenant / multi-org headers
    TENANT_HEADER: str = Field(default="x-tenant-id", description="Tenant header name")
    ORG_HEADER: str = Field(default="x-org-id", description="Organization header name")

    # External services
    ATHENA_BASE_URL: str = Field(
        default="http://localhost:7700/api/v1", description="Athena ECM base URL"
    )
    CAD_ML_BASE_URL: str = Field(
        default="http://localhost:8001", description="CAD ML Platform base URL"
    )
    DEDUP_VISION_BASE_URL: str = Field(
        default="http://localhost:8100", description="DedupCAD Vision base URL"
    )

    # Database
    DATABASE_URL: str = Field(default="sqlite:///yuantus_dev.db")
    TEST_DATABASE_URL: str = Field(default="sqlite:///:memory:")
    IDENTITY_DATABASE_URL: str = Field(
        default="",
        description="Optional separate identity DB URL; default uses DATABASE_URL",
    )
    SCHEMA_MODE: str = Field(
        default="create_all",
        description="create_all: auto-create tables (dev), migrations: use Alembic only (prod)",
    )

    # Auth (built-in / dev-first)
    AUTH_MODE: str = Field(
        default="optional", description="disabled|optional|required"
    )
    JWT_SECRET_KEY: str = Field(
        default="yuantus-dev-secret-change-me",
        description="HS256 secret for dev; override in production",
    )
    JWT_ACCESS_TOKEN_TTL_SECONDS: int = Field(
        default=3600, description="Access token TTL seconds"
    )
    AUTH_LEEWAY_SECONDS: int = Field(
        default=0, description="JWT exp leeway seconds"
    )

    AUDIT_ENABLED: bool = Field(default=False, description="Audit log middleware")

    # Search engine (optional)
    SEARCH_ENGINE_INDEX_PREFIX: str = Field(default="yuantus")
    SEARCH_ENGINE_URL: str = Field(default="")
    SEARCH_ENGINE_USERNAME: str = Field(default="")
    SEARCH_ENGINE_PASSWORD: str = Field(default="")

    # File storage (Meta Engine)
    STORAGE_TYPE: str = Field(default="local", description="local|s3")
    LOCAL_STORAGE_PATH: str = Field(default="./data/storage")
    LOCAL_STORAGE_PUBLIC_URL_PREFIX: str = Field(default="")

    # Plugins
    PLUGIN_DIRS: str = Field(
        default="./plugins", description="Comma-separated plugin directories"
    )
    PLUGINS_AUTOLOAD: bool = Field(
        default=True, description="Auto-discover/load plugins on startup"
    )
    PLUGINS_ENABLED: str = Field(
        default="",
        description="Comma-separated plugin ids to load; empty means all discovered",
    )

    S3_BUCKET_NAME: str = Field(default="yuantus")
    S3_ENDPOINT_URL: str = Field(default="http://localhost:9000")
    S3_PUBLIC_ENDPOINT_URL: str = Field(
        default="",
        description="Public S3 endpoint used in presigned URLs; defaults to S3_ENDPOINT_URL",
    )
    S3_ACCESS_KEY_ID: str = Field(default="minioadmin")
    S3_SECRET_ACCESS_KEY: str = Field(default="minioadmin")
    S3_REGION_NAME: str = Field(default="us-east-1")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
