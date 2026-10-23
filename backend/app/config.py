from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE)

    # techforce_app: what the API and the tests connect as.
    database_url: str
    test_database_url: str
    # techforce_owner: used only by app.db.apply_schema to create tables.
    owner_database_url: str
    test_owner_database_url: str

    # DECISIONS.md section 10: larger uploads are refused before they are read.
    max_upload_bytes: int = 10 * 1024 * 1024

    # Browser origins allowed to call the API: the Vite dev server.
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
