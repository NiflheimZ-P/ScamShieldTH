"""Rebuild data/index/indicators.sqlite from data/indicators/seed.csv.

    uv run python -m scripts.seed_indicators
"""

from app.config import get_settings
from app.repositories.indicators import build_db

if __name__ == "__main__":
    s = get_settings()
    n = build_db(s.indicators_csv, s.indicators_db)
    print(f"wrote {n} indicators -> {s.indicators_db}")
