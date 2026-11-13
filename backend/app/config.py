from functools import lru_cache

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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

