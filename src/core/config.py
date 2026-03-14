
from typing import Optional, List, Dict, Any, Union
from pydantic_settings import BaseSettings
from pydantic import Field, validator, AnyHttpUrl, SecretStr
from functools import lru_cache
import json
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class AuthConfig(BaseSettings):
    """Authentication configuration"""
    jwt_secret_key: SecretStr = Field(..., validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(30, validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(7, validation_alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    oauth2_providers: Dict[str, Any] = Field(default_factory=dict, validation_alias="OAUTH2_PROVIDERS")
    api_key_header_name: str = Field("X-API-Key", validation_alias="API_KEY_HEADER_NAME")
    
    mfa_enabled: bool = Field(False, validation_alias="MFA_ENABLED")
    mfa_issuer_name: str = Field("Enterprise Security Orchestrator", validation_alias="MFA_ISSUER_NAME")
    
    @validator("oauth2_providers", pre=True)
    def parse_oauth2_providers(cls, v):
        if isinstance(v, str):
            return json.loads(v) if v else {}
        return v
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration"""
    enabled: bool = Field(True, validation_alias="RATE_LIMIT_ENABLED")
    default_limit: str = Field("100/minute", validation_alias="RATE_LIMIT_DEFAULT")
    strategy: str = Field("fixed-window", validation_alias="RATE_LIMIT_STRATEGY")
    
    redis_url: Optional[str] = Field(None, validation_alias="REDIS_URL")
    redis_prefix: str = Field("rate_limit:", validation_alias="RATE_LIMIT_REDIS_PREFIX")
    
    endpoint_limits: Dict[str, str] = Field(default_factory=dict, validation_alias="RATE_LIMIT_ENDPOINTS")
    user_limits: Dict[str, str] = Field(default_factory=dict, validation_alias="RATE_LIMIT_USERS")
    tenant_limits: Dict[str, str] = Field(default_factory=dict, validation_alias="RATE_LIMIT_TENANTS")
    
    @validator("endpoint_limits", "user_limits", "tenant_limits", pre=True)
    def parse_limits(cls, v):
        if isinstance(v, str):
            return json.loads(v) if v else {}
        return v
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class EncryptionConfig(BaseSettings):
    """Encryption configuration"""
    tls_enabled: bool = Field(True, validation_alias="TLS_ENABLED")
    tls_cert_path: Optional[str] = Field(None, validation_alias="TLS_CERT_PATH")
    tls_key_path: Optional[str] = Field(None, validation_alias="TLS_KEY_PATH")
    
    field_encryption_key: SecretStr = Field(..., validation_alias="FIELD_ENCRYPTION_KEY")
    field_encryption_algorithm: str = Field("AES-256-GCM", validation_alias="FIELD_ENCRYPTION_ALGORITHM")
    
    db_encryption_enabled: bool = Field(True, validation_alias="DB_ENCRYPTION_ENABLED")
    db_encryption_key: Optional[SecretStr] = Field(None, validation_alias="DB_ENCRYPTION_KEY")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class ObservabilityConfig(BaseSettings):
    """Observability configuration"""
    service_name: str = Field("security-orchestrator", validation_alias="SERVICE_NAME")
    environment: Environment = Field(Environment.DEVELOPMENT, validation_alias="ENVIRONMENT")
    
    otlp_endpoint: Optional[str] = Field(None, validation_alias="OTLP_ENDPOINT")
    traces_enabled: bool = Field(True, validation_alias="TRACES_ENABLED")
    traces_sample_rate: float = Field(0.1, validation_alias="TRACES_SAMPLE_RATE")
    
    metrics_enabled: bool = Field(True, validation_alias="METRICS_ENABLED")
    metrics_port: int = Field(9090, validation_alias="METRICS_PORT")
    
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field("json", validation_alias="LOG_FORMAT")
    audit_log_enabled: bool = Field(True, validation_alias="AUDIT_LOG_ENABLED")
    audit_log_path: str = Field("/var/log/audit.log", validation_alias="AUDIT_LOG_PATH")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    postgres_dsn: str = Field(..., validation_alias="POSTGRES_DSN")
    redis_dsn: str = Field(..., validation_alias="REDIS_DSN")
    mongodb_dsn: Optional[str] = Field(None, validation_alias="MONGODB_DSN")
    
    db_pool_min_size: int = Field(10, validation_alias="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(20, validation_alias="DB_POOL_MAX_SIZE")
    db_pool_timeout: int = Field(30, validation_alias="DB_POOL_TIMEOUT")
    
    db_retry_attempts: int = Field(3, validation_alias="DB_RETRY_ATTEMPTS")
    db_retry_delay: int = Field(1, validation_alias="DB_RETRY_DELAY")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class SecurityConfig(BaseSettings):
    """Security configuration"""
    cors_origins: Union[str, List[str]] = Field(
        "http://localhost:3000", 
        validation_alias="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(True, validation_alias="CORS_ALLOW_CREDENTIALS")
    
    allowed_hosts: Union[str, List[str]] = Field(
        "localhost,127.0.0.1", 
        validation_alias="ALLOWED_HOSTS"
    )
    
    security_headers_enabled: bool = Field(True, validation_alias="SECURITY_HEADERS_ENABLED")
    hsts_enabled: bool = Field(True, validation_alias="HSTS_ENABLED")
    hsts_max_age: int = Field(31536000, validation_alias="HSTS_MAX_AGE")
    
    ip_whitelist: Union[str, List[str]] = Field(
        "", 
        validation_alias="IP_WHITELIST"
    )
    ip_blacklist: Union[str, List[str]] = Field(
        "", 
        validation_alias="IP_BLACKLIST"
    )
    
    max_request_size: int = Field(10 * 1024 * 1024, validation_alias="MAX_REQUEST_SIZE")
    max_request_body_limit: int = Field(10 * 1024 * 1024, validation_alias="MAX_REQUEST_BODY_LIMIT")
    
    @validator("cors_origins", "allowed_hosts", "ip_whitelist", "ip_blacklist", pre=True)
    def parse_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            if not v.strip():
                return []
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class LLMConfig(BaseSettings):
    """LLM Configuration"""
    provider: str = Field("openai", validation_alias="LLM_PROVIDER")
    openai_api_key: Optional[str] = Field(None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, validation_alias="ANTHROPIC_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_key: Optional[str] = Field(None, validation_alias="AZURE_OPENAI_KEY")
    local_llm_url: str = Field("http://localhost:11434", validation_alias="LOCAL_LLM_URL")
    local_llm_model: str = Field("llama2", validation_alias="LOCAL_LLM_MODEL")
    
    max_tokens_per_request: int = Field(4000, validation_alias="MAX_TOKENS_PER_REQUEST")
    token_buffer: int = Field(500, validation_alias="TOKEN_BUFFER")
    
    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = True


class MemoryConfig(BaseSettings):
    """Memory System Configuration"""
    vector_db_type: str = Field("pinecone", validation_alias="VECTOR_DB_TYPE")
    pinecone_api_key: Optional[str] = Field(None, validation_alias="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(None, validation_alias="PINECONE_ENVIRONMENT")
    
    graph_db_type: str = Field("neo4j", validation_alias="GRAPH_DB_TYPE")
    neo4j_uri: Optional[str] = Field(None, validation_alias="NEO4J_URI")
    neo4j_user: Optional[str] = Field(None, validation_alias="NEO4J_USER")
    neo4j_password: Optional[str] = Field(None, validation_alias="NEO4J_PASSWORD")
    
    timeseries_db_type: str = Field("influxdb", validation_alias="TIMESERIES_DB_TYPE")
    influxdb_url: Optional[str] = Field(None, validation_alias="INFLUXDB_URL")
    influxdb_token: Optional[str] = Field(None, validation_alias="INFLUXDB_TOKEN")
    influxdb_org: Optional[str] = Field(None, validation_alias="INFLUXDB_ORG")
    influxdb_bucket: str = Field("eso_metrics", validation_alias="INFLUXDB_BUCKET")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class Settings(BaseSettings):
    """Main settings class combining all configurations"""
    
    # Environment
    environment: Environment = Field(Environment.DEVELOPMENT, validation_alias="ENVIRONMENT")
    debug: bool = Field(False, validation_alias="DEBUG")
    
    # API Configuration
    api_version: str = Field("v1", validation_alias="API_VERSION")
    api_prefix: str = Field("/api", validation_alias="API_PREFIX")
    api_port: int = Field(8000, validation_alias="API_PORT")
    api_host: str = Field("0.0.0.0", validation_alias="API_HOST")
    workers: int = Field(4, validation_alias="WORKERS")
    
    # Sub-configurations - initialize with default values that will be overridden by env
    auth: AuthConfig = Field(default_factory=AuthConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    encryption: EncryptionConfig = Field(default_factory=EncryptionConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    
    # MLFlow Configuration
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "security_orchestrator"
    mlflow_registry_uri: Optional[str] = None
    
    # Feature flags
    features_enabled: Dict[str, bool] = Field(
        default={
            "hybrid_execution": True,
            "audit_logging": True,
            "mfa": False,
            "webhooks": True,
            "scheduling": True
        },
        validation_alias="FEATURES_ENABLED"
    )
    
    @validator("features_enabled", pre=True)
    def parse_features(cls, v):
        if isinstance(v, str):
            return json.loads(v) if v else {}
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings loader"""
    return Settings()
