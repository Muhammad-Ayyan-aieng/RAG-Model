from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):

    # ================================
    # LLM Configuration (Groq)
    # ================================
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ================================
    # Admin Authentication
    # ================================
    ADMIN_PASSWORD: str

    # ================================
    # Vector Database (Qdrant)
    # ================================
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str = "documents"
    QDRANT_VECTOR_SIZE: int = 384

    # ================================
    # Supabase Configuration (NEW)
    # ================================
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str

    # ================================
    # JWT Configuration (NEW)
    # ================================
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_EXPIRATION_MINUTES: int = 60 * 24  # 24 hours

    # ================================
    # Public User Limits
    # ================================
    PUBLIC_MAX_FILE_SIZE_MB: int = 5
    PUBLIC_MAX_FILES_COUNT: int = 3
    PUBLIC_ALLOWED_EXTENSIONS: str = "pdf,txt"

    # ================================
    # App Settings
    # ================================
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # ================================
    # Computed / derived
    # ================================
    @field_validator("GROQ_API_KEY")
    @classmethod
    def groq_key_must_not_be_empty(cls, v: str) -> str:
        if not v or v == "your_groq_api_key_here":
            raise ValueError("GROQ_API_KEY is not set in your .env file")
        return v
    
    @field_validator("QDRANT_API_KEY")
    @classmethod
    def qdrant_key_must_not_be_empty(cls, v: str) -> str:
        if not v or v == "your_qdrant_api_key_here":
            raise ValueError("QDRANT_API_KEY is not set in your .env file")
        return v

    @field_validator("ADMIN_PASSWORD")
    @classmethod
    def admin_password_must_not_be_empty(cls, v: str) -> str:
        if not v or v == "choose_a_strong_password_here":
            raise ValueError("ADMIN_PASSWORD is not set in your .env file")
        return v

    # NEW: Supabase validators
    @field_validator("SUPABASE_URL")
    @classmethod
    def supabase_url_must_not_be_empty(cls, v: str) -> str:
        if not v or v == "your_supabase_url_here":
            raise ValueError("SUPABASE_URL is not set in your .env file")
        return v

    @field_validator("SUPABASE_ANON_KEY")
    @classmethod
    def supabase_key_must_not_be_empty(cls, v: str) -> str:
        if not v or v == "your_supabase_anon_key_here":
            raise ValueError("SUPABASE_ANON_KEY is not set in your .env file")
        return v

    # NEW: JWT validator (optional, just a warning if default is used)
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def jwt_secret_should_be_strong(cls, v: str) -> str:
        if v == "your-secret-key-change-this-in-production":
            print("WARNING: Using default JWT_SECRET_KEY. Change this in production!")
        return v

    def get_allowed_extensions(self) -> List[str]:
        return [ext.strip().lower() for ext in self.PUBLIC_ALLOWED_EXTENSIONS.split(",")]

    def get_max_file_size_bytes(self) -> int:
        return self.PUBLIC_MAX_FILE_SIZE_MB * 1024 * 1024

    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single instance, imported everywhere
settings = Settings()