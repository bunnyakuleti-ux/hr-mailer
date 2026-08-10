from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:5173"
    SECRET_KEY: str = "change_this_secret_key_in_production"
    MAX_ATTACHMENT_SIZE_MB: int = 10
    DEFAULT_DELAY_SECONDS: float = 2.0
    MAX_RECIPIENTS_PER_CAMPAIGN: int = 2000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
