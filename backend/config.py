import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Aplikasi konfigurasi menggunakan pydantic-settings."""
    REDIS_URL: str = "redis://redis:6379/0"
    WORKSPACE_ROOT: str = "/workspace/sandbox"
    PROJECT_NAME: str = "SIGMA Platform"
    DATABASE_URL: str = "mysql://sigma:sigma_password@mariadb:3306/sigma"
    SECRET_KEY: str = "dev-insecure-change-me"
    
    # LLM & Simulation Config
    LLM_PROVIDER: str = "simulated"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_MODEL: str = "claude-sonnet-4-6"
    OPENAI_MODEL: str = "gpt-5.5"
    SIMULATION_STEP_DELAY_SECONDS: float = 2.0
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
