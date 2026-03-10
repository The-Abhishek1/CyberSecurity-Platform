from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field, validator, AnyHttpUrl, SecretStr
from functools import lru_cache
import json
import os


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class AuthConfig(BaseSettings):
    """Authentication configuration"""
    jwt_secret_key: SecretStr = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    oauth2_providers: Dict[str, Any] = Field(default_factory=dict, env="OAUTH2_PROVIDERS")
    api_key_header_name: str = Field("X-API-Key", env="API_KEY_HEADER_NAME")
    
    mfa_enabled: bool = Field(False, env="MFA_ENABLED")
    mfa_issuer_name: str = Field("Enterprise Security Orchestrator", env="MFA_ISSUER_NAME")
    
    @validator("oauth2_providers", pre=True)
    def parse_oauth2_providers(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration"""
    enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    default_limit: str = Field("100/minute", env="RATE_LIMIT_DEFAULT")
    strategy: str = Field("fixed-window", env="RATE_LIMIT_STRATEGY")  # fixed-window, sliding-window, token-bucket
    
    # Redis for distributed rate limiting
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    redis_prefix: str = Field("rate_limit:", env="RATE_LIMIT_REDIS_PREFIX")
    
    # Per endpoint limits
    endpoint_limits: Dict[str, str] = Field(default_factory=dict, env="RATE_LIMIT_ENDPOINTS")
    
    # Per user/tenant limits
    user_limits: Dict[str, str] = Field(default_factory=dict, env="RATE_LIMIT_USERS")
    tenant_limits: Dict[str, str] = Field(default_factory=dict, env="RATE_LIMIT_TENANTS")
    
    @validator("endpoint_limits", "user_limits", "tenant_limits", pre=True)
    def parse_limits(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class EncryptionConfig(BaseSettings):
    """Encryption configuration for data at rest and in transit"""
    tls_enabled: bool = Field(True, env="TLS_ENABLED")
    tls_cert_path: Optional[str] = Field(None, env="TLS_CERT_PATH")
    tls_key_path: Optional[str] = Field(None, env="TLS_KEY_PATH")
    
    # Field-level encryption
    field_encryption_key: SecretStr = Field(..., env="FIELD_ENCRYPTION_KEY")
    field_encryption_algorithm: str = Field("AES-256-GCM", env="FIELD_ENCRYPTION_ALGORITHM")
    
    # Database encryption
    db_encryption_enabled: bool = Field(True, env="DB_ENCRYPTION_ENABLED")
    db_encryption_key: Optional[SecretStr] = Field(None, env="DB_ENCRYPTION_KEY")


class ObservabilityConfig(BaseSettings):
    """Observability configuration"""
    service_name: str = Field("security-orchestrator", env="SERVICE_NAME")
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    
    # OpenTelemetry
    otlp_endpoint: Optional[str] = Field(None, env="OTLP_ENDPOINT")
    traces_enabled: bool = Field(True, env="TRACES_ENABLED")
    traces_sample_rate: float = Field(0.1, env="TRACES_SAMPLE_RATE")
    
    # Metrics
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")  # json or console
    audit_log_enabled: bool = Field(True, env="AUDIT_LOG_ENABLED")
    audit_log_path: str = Field("/var/log/audit.log", env="AUDIT_LOG_PATH")


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    postgres_dsn: str = Field(..., env="POSTGRES_DSN")
    redis_dsn: str = Field(..., env="REDIS_DSN")
    mongodb_dsn: Optional[str] = Field(None, env="MONGODB_DSN")
    
    # Connection pooling
    db_pool_min_size: int = Field(10, env="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(20, env="DB_POOL_MAX_SIZE")
    db_pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    
    # Retry configuration
    db_retry_attempts: int = Field(3, env="DB_RETRY_ATTEMPTS")
    db_retry_delay: int = Field(1, env="DB_RETRY_DELAY")  # seconds


class SecurityConfig(BaseSettings):
    """Security configuration"""
    cors_origins: List[AnyHttpUrl] = Field(["http://localhost:3000"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    
    allowed_hosts: List[str] = Field(["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    
    # Security headers
    security_headers_enabled: bool = Field(True, env="SECURITY_HEADERS_ENABLED")
    hsts_enabled: bool = Field(True, env="HSTS_ENABLED")
    hsts_max_age: int = Field(31536000, env="HSTS_MAX_AGE")
    
    # IP whitelisting/blacklisting
    ip_whitelist: List[str] = Field(default_factory=list, env="IP_WHITELIST")
    ip_blacklist: List[str] = Field(default_factory=list, env="IP_BLACKLIST")
    
    # Request validation
    max_request_size: int = Field(10 * 1024 * 1024, env="MAX_REQUEST_SIZE")  # 10MB
    max_request_body_limit: int = Field(10 * 1024 * 1024, env="MAX_REQUEST_BODY_LIMIT")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class Settings(BaseSettings):
    """Main settings class combining all configurations"""
    
    # Environment
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # API Configuration
    api_version: str = Field("v1", env="API_VERSION")
    api_prefix: str = Field("/api", env="API_PREFIX")
    api_port: int = Field(8000, env="API_PORT")
    api_host: str = Field("0.0.0.0", env="API_HOST")
    workers: int = Field(4, env="WORKERS")
    
    # Sub-configurations
    auth: AuthConfig = AuthConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    encryption: EncryptionConfig = EncryptionConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig = SecurityConfig()
    
    # Feature flags
    features_enabled: Dict[str, bool] = Field(
        default={
            "hybrid_execution": True,
            "audit_logging": True,
            "mfa": False,
            "webhooks": True,
            "scheduling": True
        },
        env="FEATURES_ENABLED"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings loader"""
    return Settings()


class LLMConfig(BaseSettings):
    """LLM Configuration"""
    provider: str = Field("openai", env="LLM_PROVIDER")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_key: Optional[str] = Field(None, env="AZURE_OPENAI_KEY")
    local_llm_url: str = Field("http://localhost:11434", env="LOCAL_LLM_URL")
    local_llm_model: str = Field("llama2", env="LOCAL_LLM_MODEL")
    
    # Token tracking
    max_tokens_per_request: int = Field(4000, env="MAX_TOKENS_PER_REQUEST")
    token_buffer: int = Field(500, env="TOKEN_BUFFER")


class MemoryConfig(BaseSettings):
    """Memory System Configuration"""
    vector_db_type: str = Field("pinecone", env="VECTOR_DB_TYPE")
    pinecone_api_key: Optional[str] = Field(None, env="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(None, env="PINECONE_ENVIRONMENT")
    
    graph_db_type: str = Field("neo4j", env="GRAPH_DB_TYPE")
    neo4j_uri: Optional[str] = Field(None, env="NEO4J_URI")
    neo4j_user: Optional[str] = Field(None, env="NEO4J_USER")
    neo4j_password: Optional[str] = Field(None, env="NEO4J_PASSWORD")
    
    timeseries_db_type: str = Field("influxdb", env="TIMESERIES_DB_TYPE")
    influxdb_url: Optional[str] = Field(None, env="INFLUXDB_URL")
    influxdb_token: Optional[str] = Field(None, env="INFLUXDB_TOKEN")
    influxdb_org: Optional[str] = Field(None, env="INFLUXDB_ORG")
    influxdb_bucket: str = Field("eso_metrics", env="INFLUXDB_BUCKET")


# Add to Settings class
class Settings(BaseSettings):
    # ... existing fields ...
    
    llm: LLMConfig = LLMConfig()
    memory: MemoryConfig = MemoryConfig()