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
    # ChromaDB
    # ================================
    CHROMA_PATH: str = "./chroma_data"
    CHROMA_COLLECTION_NAME: str = "documents"

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

    @field_validator("ADMIN_PASSWORD")
    @classmethod
    def admin_password_must_not_be_empty(cls, v: str) -> str:
        if not v or v == "choose_a_strong_password_here":
            raise ValueError("ADMIN_PASSWORD is not set in your .env file")
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