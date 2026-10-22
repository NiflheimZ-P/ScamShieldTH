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
    brands_csv: Path = REPO_ROOT / "data" / "indicators" / "brands.csv"
    indicators_db: Path = REPO_ROOT / "data" / "index" / "indicators.sqlite"  # built from the CSV
    agent_max_steps: int = 6
    verdict_max_repairs: int = 2
    retrieval_mode: str = "hybrid"  # dense | bm25 | hybrid — hybrid won on the dev split, see eval/run_retrieval.py
    min_score: float = 0.40  # dense-cosine gate, chosen on the dev split (R@3 0.773 vs 0.636 at 0.45) — eval/run_retrieval.py


@lru_cache
def get_settings() -> Settings:
    return Settings()
