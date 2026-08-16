from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    embedding_device: str = "cpu"
    embedding_model: str = "all-MiniLM-L6-v2"

    semantic_weight: float = 0.6
    keyword_weight: float = 0.4

    # Optional: unlocks onsite/local listings via Adzuna. Free key from
    # https://developer.adzuna.com/ - the keyless boards work without it.
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    database_path: Path = Path("./data/resume_matcher.db")
    upload_dir: Path = Path("./data/uploads")

    @property
    def weights_valid(self) -> bool:
        return abs(self.semantic_weight + self.keyword_weight - 1.0) < 1e-6


settings = Settings()
