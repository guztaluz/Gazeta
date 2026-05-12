from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# .env must win over OS-level env vars (e.g. shells that pre-set ANTHROPIC_API_KEY="").
load_dotenv(PROJECT_ROOT / ".env", override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_port: int = 8080
    log_level: str = "INFO"
    printer_driver: str = Field(default="mock", pattern="^(mock|ble)$")

    printer_mac: str = ""
    printer_width_px: int = 384

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"

    weather_lat: float = 53.35
    weather_lon: float = -6.26
    weather_tz: str = "Europe/Dublin"

    google_client_secret_path: Path = PROJECT_ROOT / "secrets" / "client_secret.json"
    google_token_path: Path = PROJECT_ROOT / "secrets" / "google_token.json"

    output_dir: Path = PROJECT_ROOT / "output"

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
