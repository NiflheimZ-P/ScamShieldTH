"""The single place that talks to the class proxy (gemma-4-E4B-it + bge-m3)."""

from functools import lru_cache

from openai import AsyncOpenAI

from app.config import get_settings


@lru_cache
def get_llm_client() -> AsyncOpenAI:
    s = get_settings()
    # The class proxy caps tokens per short window and answers 429 when a burst exceeds it; the SDK retries
    # 429/5xx with exponential backoff, so a few extra retries ride out the window instead of failing a scan.
    return AsyncOpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url, max_retries=6, timeout=90)
