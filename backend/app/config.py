from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Akıllı Oto Servis API"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://autoservis:autoservis_dev@db:5432/autoservis"
    cors_origins: str = "http://localhost:5173"
    audio_storage_path: str = "/app/audio-data"
    model_cache_dir: str = "/app/model-cache"
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    embedding_model: str = "intfloat/multilingual-e5-small"
    max_audio_size_mb: int = 25
    auth_secret: str = "change-this-development-secret"
    auth_cookie_name: str = "autoservis_session"
    auth_cookie_secure: bool = False
    local_auth_enabled: bool = True
    local_login_code: str = Field(default="111111", pattern=r"^\d{6}$")
    otp_expiry_minutes: int = 10
    otp_request_interval_seconds: int = 60
    otp_max_attempts: int = 5
    session_expiry_days: int = 7
    test_3d_secure_code: str = Field(default="123456", pattern=r"^\d{6}$")
    test_3d_expiry_minutes: int = 5
    test_3d_max_attempts: int = 3
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    mail_from: str = "Akıllı Oto Servis <noreply@akilli-servis.local>"
    mailpit_public_url: str = "http://localhost:8026"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

