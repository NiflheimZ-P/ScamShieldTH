"""Settings read from the environment (.env). Never hard-code keys."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    openai_api_key: str
    openai_base_url: str = "https://llm.nat-d.uk/v1"
    chat_model: str = "gemma-4-E4B-it"
    embed_model: str = "bge-m3"

    data_dir: Path = REPO_ROOT / "data"
    indicators_csv: Path = REPO_ROOT / "data" / "indicators" / "seed.csv"
    indicators_db: Path = REPO_ROOT / "data" / "index" / "indicators.sqlite"  # built from the CSV
    agent_max_steps: int = 6
    verdict_max_repairs: int = 2
    retrieval_mode: str = "hybrid"  # dense | bm25 | hybrid — chosen on the eval set, see eval/run_retrieval.py
    min_score: float = 0.45  # dense-cosine gate, tuned on the eval set — see eval/run_retrieval.py


@lru_cache
def get_settings() -> Settings:
    return Settings()
