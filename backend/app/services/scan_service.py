"""Service layer: orchestrates the agent and emits SSE events.

Event contract (one JSON object per `data:` frame, then `data: [DONE]`; mirrored in
frontend/src/lib/types.ts):
  {"type": "step", "id": str, "tool": str, "args": dict}            agent called a tool (id = tool_call id)
  {"type": "observation", "id": str, "tool": str, "summary": str,
   "tone": "warn" | "ok" | "info"}                                  short result of that call
  {"type": "summarizing"}                                           tools done, writing the verdict
  {"type": "verdict", "verdict": Verdict}                           final validated answer
  {"type": "error", "message": str}                                 failure after the stream started

check_indicator args carry "kind" (phone | domain | line_id | bank_account) and "value".
"""

import json
import logging
from collections.abc import AsyncIterator
from functools import lru_cache

from app.agent.loop import run_agent
from app.agent.tools import SearchConfig, Toolbox
from app.agent.verdict import VerdictError
from app.api.schemas import ScanRequest
from app.config import get_settings
from app.llm.client import get_llm_client
from app.repositories.advisories import AdvisoryRepository
from app.repositories.indicators import IndicatorRepository

log = logging.getLogger(__name__)


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_toolbox(use_rag: bool = True, mode: str | None = None, min_score: float | None = None) -> Toolbox:
    """use_rag=False (or no built index) leaves search_advisories out of the allow-list."""
    s = get_settings()
    indicators = IndicatorRepository(s.indicators_db, s.indicators_csv)
    advisories = AdvisoryRepository(s.data_dir)
    search = None
    if use_rag and advisories.index_exists():
        search = SearchConfig(
            retriever=advisories.retriever(), client=get_llm_client(), embed_model=s.embed_model,
            mode=mode or s.retrieval_mode, min_score=s.min_score if min_score is None else min_score,
        )
    elif use_rag:
        log.warning("advisory index missing — running without search_advisories (scripts/build_index.py)")
    return Toolbox(indicators, search)


@lru_cache
def get_toolbox() -> Toolbox:
    return build_toolbox()


class ScanService:
    async def scan_stream(self, req: ScanRequest) -> AsyncIterator[str]:
        s = get_settings()
        try:
            async for event in run_agent(
                get_llm_client(), get_toolbox(), req.message,
                model=s.chat_model, max_steps=s.agent_max_steps, max_repairs=s.verdict_max_repairs,
            ):
                event.pop("repairs", None)  # eval-only detail, not part of the UI contract
                yield sse(event)
        except VerdictError:
            log.exception("verdict failed")
            yield sse({"type": "error", "message": "ระบบสรุปผลไม่สำเร็จ ลองใหม่อีกครั้ง"})
        except Exception:  # upstream died mid-stream -> error frame, not silence
            log.exception("scan failed")
            yield sse({"type": "error", "message": "เชื่อมต่อโมเดลไม่สำเร็จ ลองใหม่อีกครั้ง"})
        yield "data: [DONE]\n\n"
