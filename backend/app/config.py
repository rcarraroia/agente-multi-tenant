from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Agente Multi-Tenant API"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_ANON_KEY: Optional[str] = None

    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    BACKEND_CORS_ORIGINS: list[str] = []
    CORS_ORIGINS: str = ""  # Comma-separated origins from .env
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS env var as comma-separated list."""
        if self.CORS_ORIGINS:
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS
    
    # Supabase Auth (para validar tokens JWT do Slim Quality)
    SUPABASE_JWT_SECRET: Optional[str] = None  # Obtido em Supabase Dashboard > Settings > API > JWT Secret

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # External Integrations
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    AGENT_TEMPERATURE: float = 0.7
    AGENT_MEMORY_WINDOW: int = 20

    EVOLUTION_API_URL: Optional[str] = None
    EVOLUTION_API_KEY: Optional[str] = None
    CHATWOOT_URL: Optional[str] = None
    CHATWOOT_API_KEY: Optional[str] = None
    CHATWOOT_ADMIN_TOKEN: Optional[str] = None
    CHATWOOT_ACCOUNT_ID: Optional[str] = None

settings = Settings()
