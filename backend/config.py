import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Aplikasi konfigurasi menggunakan pydantic-settings."""
    REDIS_URL: str = "redis://redis:6379/0"
    WORKSPACE_ROOT: str = "/workspace/sandbox"
    PROJECT_NAME: str = "SIGMA Platform"
    
    # LLM & Simulation Config
    LLM_PROVIDER: str = "simulated"
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_MODEL: str = "claude-sonnet-4-6"
    SIMULATION_STEP_DELAY_SECONDS: float = 2.0
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
