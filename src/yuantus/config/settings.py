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
    PLATFORM_ADMIN_ENABLED: bool = Field(
        default=False,
        description="Enable platform admin capabilities for cross-tenant provisioning",
    )
    PLATFORM_TENANT_ID: str = Field(
        default="platform",
        description="Tenant id used for platform admin operations",
    )
    RELATIONSHIP_SIMULATE_ENABLED: bool = Field(
        default=False,
        description="Allow debug endpoint to simulate deprecated relationship writes",
    )
    RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED: bool = Field(
        default=False,
        description="Seed legacy meta_relationship_types rows for compatibility",
    )
    QUOTA_MODE: str = Field(
        default="disabled",
        description="disabled|soft|enforce quota checks for tenant limits",
    )

    # External services
    ATHENA_BASE_URL: str = Field(
        default="http://localhost:7700/api/v1", description="Athena ECM base URL"
    )
    ATHENA_SERVICE_TOKEN: str = Field(
        default="",
        description="Optional service token (JWT) for Athena ECM integrations",
    )
    ATHENA_TOKEN_URL: str = Field(
        default="",
        description="Optional Athena OAuth token URL for client credentials",
    )
    ATHENA_CLIENT_ID: str = Field(
        default="",
        description="Optional Athena OAuth client id for service account",
    )
    ATHENA_CLIENT_SECRET: str = Field(
        default="",
        description="Optional Athena OAuth client secret for service account",
    )
    ATHENA_CLIENT_SECRET_FILE: str = Field(
        default="",
        description="Optional file path for Athena client secret (preferred)",
    )
    ATHENA_CLIENT_SCOPE: str = Field(
        default="",
        description="Optional OAuth scope for Athena client credentials",
    )
    CAD_ML_BASE_URL: str = Field(
        default="http://localhost:8001", description="CAD ML Platform base URL"
    )
    DEDUP_VISION_BASE_URL: str = Field(
        default="http://localhost:8100", description="DedupCAD Vision base URL"
    )
    DEDUP_VISION_SERVICE_TOKEN: str = Field(
        default="",
        description="Optional service token (JWT) for DedupCAD Vision integrations",
    )
    CAD_ML_SERVICE_TOKEN: str = Field(
        default="",
        description="Optional service token (JWT) for CAD ML Platform integrations",
    )
    CAD_EXTRACTOR_BASE_URL: str = Field(
        default="",
        description="Optional CAD extractor service base URL",
    )
    CAD_EXTRACTOR_SERVICE_TOKEN: str = Field(
        default="",
        description="Optional service token (JWT) for CAD extractor service",
    )
    CAD_EXTRACTOR_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="CAD extractor service timeout in seconds",
    )
    CAD_EXTRACTOR_MODE: str = Field(
        default="optional",
        description="optional|required (fail cad_extract when external service fails)",
    )
    CAD_CONNECTOR_BASE_URL: str = Field(
        default="",
        description="Optional CAD connector service base URL",
    )
    CAD_CONNECTOR_SERVICE_TOKEN: str = Field(
        default="",
        description="Optional service token (JWT) for CAD connector service",
    )
    CAD_CONNECTOR_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="CAD connector service timeout in seconds",
    )
    CAD_CONNECTOR_MODE: str = Field(
        default="optional",
        description="disabled|optional|required (fail when CAD connector fails)",
    )
    CAD_CONNECTORS_CONFIG_PATH: str = Field(
        default="",
        description="Optional JSON config path for custom CAD connectors",
    )
    CAD_CONNECTORS_ALLOW_PATH_OVERRIDE: bool = Field(
        default=False,
        description="Allow reload endpoint to accept config_path override (admin only)",
    )
    CADGF_ROOT: str = Field(
        default="",
        description="Path to CADGameFusion repo root (for 2D CAD conversion)",
    )
    CADGF_CONVERT_SCRIPT: str = Field(
        default="",
        description="Path to CADGameFusion tools/plm_convert.py",
    )
    CADGF_CONVERT_CLI: str = Field(
        default="",
        description="Path to CADGameFusion convert_cli binary",
    )
    CADGF_DXF_PLUGIN_PATH: str = Field(
        default="",
        description="Path to CADGameFusion DXF importer plugin",
    )
    CADGF_PYTHON_BIN: str = Field(
        default="",
        description="Override python executable for CADGF conversion",
    )
    CADGF_ROUTER_BASE_URL: str = Field(
        default="http://127.0.0.1:9000",
        description="CADGameFusion router service base URL",
    )
    CADGF_ROUTER_PUBLIC_BASE_URL: str = Field(
        default="",
        description="Public CADGameFusion router base URL for viewer links",
    )
    CADGF_ROUTER_AUTH_TOKEN: str = Field(
        default="",
        description="Bearer token for CADGameFusion router service",
    )
    CADGF_DEFAULT_EMIT: str = Field(
        default="json,gltf,meta",
        description="Default emit mode for CAD preview bridge",
    )
    CADGF_ROUTER_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Timeout for CADGameFusion router requests",
    )
    DWG_CONVERTER_BIN: str = Field(
        default="",
        description="Optional DWG->DXF converter binary (e.g. ODAFileConverter).",
    )
    CAD_PREVIEW_PUBLIC: bool = Field(
        default=False,
        description="Allow unauthenticated access to CAD preview assets",
    )
    CAD_PREVIEW_CORS_ORIGINS: str = Field(
        default="",
        description="Comma-separated CORS origins for CAD preview assets",
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
    ESIGN_SECRET_KEY: str = Field(
        default="",
        description="Optional HMAC secret for electronic signatures (defaults to JWT_SECRET_KEY)",
    )
    JWT_ACCESS_TOKEN_TTL_SECONDS: int = Field(
        default=3600, description="Access token TTL seconds"
    )
    AUTH_LEEWAY_SECONDS: int = Field(
        default=0, description="JWT exp leeway seconds"
    )

    AUDIT_ENABLED: bool = Field(default=False, description="Audit log middleware")
    AUDIT_RETENTION_DAYS: int = Field(
        default=0, description="Prune audit logs older than N days (0=disabled)"
    )
    AUDIT_RETENTION_MAX_ROWS: int = Field(
        default=0, description="Keep at most N audit rows (0=disabled)"
    )
    AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS: int = Field(
        default=600, description="Min seconds between audit prune runs"
    )
    HEALTHCHECK_EXTERNAL: bool = Field(
        default=False, description="Enable external dependency checks in /health/deps"
    )
    HEALTHCHECK_EXTERNAL_TIMEOUT_SECONDS: int = Field(
        default=2, description="Timeout for external dependency checks"
    )

    # Search engine (optional)
    SEARCH_ENGINE_INDEX_PREFIX: str = Field(default="yuantus")
    SEARCH_ENGINE_URL: str = Field(default="")
    SEARCH_ENGINE_USERNAME: str = Field(default="")
    SEARCH_ENGINE_PASSWORD: str = Field(default="")

    # File storage (Meta Engine)
    STORAGE_TYPE: str = Field(default="local", description="local|s3")
    LOCAL_STORAGE_PATH: str = Field(default="./data/storage")
    LOCAL_STORAGE_PUBLIC_URL_PREFIX: str = Field(default="")
    FILE_UPLOAD_MAX_BYTES: int = Field(
        default=0,
        description="Max upload size in bytes (0 disables limit)",
    )
    FILE_ALLOWED_EXTENSIONS: str = Field(
        default="",
        description="Comma-separated allowed file extensions (no dot). Empty allows all.",
    )

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

    # Jobs / Async
    JOB_MAX_ATTEMPTS_DEFAULT: int = Field(
        default=3, description="Default max attempts for async jobs"
    )
    JOB_RETRY_BACKOFF_SECONDS: int = Field(
        default=5, description="Retry backoff seconds"
    )
    JOB_STALE_TIMEOUT_SECONDS: int = Field(
        default=900, description="Requeue processing jobs after this timeout (seconds)"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Backward-compatible module-level settings instance.
settings = get_settings()
