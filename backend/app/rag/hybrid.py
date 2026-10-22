"""Retrieval modes over one index: dense (bge-m3 cosine), BM25, and hybrid via Reciprocal Rank Fusion.

`min_score` gates on dense cosine similarity in the dense and hybrid modes: a chunk below it is dropped
even if BM25 likes it, so an unrelated message (e.g. a genuine OTP) can come back with no advisories
instead of the "least bad" ones. Its value is tuned on the eval set — see eval/run_retrieval.py.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np

from app.rag.bm25 import BM25, tokenize
from app.rag.store import Index, StoredChunk

Mode = Literal["dense", "bm25", "hybrid"]
RRF_K = 60  # standard constant from Cormack et al. (2009)
POOL = 20  # candidates taken from each list before fusion


@dataclass(frozen=True)
class Hit:
    chunk: StoredChunk
    score: float  # mode-specific: cosine, BM25 or RRF
    cosine: float


class Retriever:
    def __init__(self, index: Index):
        self.index = index
        self.bm25 = BM25([tokenize(c.text + " " + c.title) for c in index.chunks])

    def search(self, query_vec: np.ndarray | None, query_text: str, *, mode: Mode, k: int,
               min_score: float) -> list[Hit]:
        cos = self.index.vectors @ query_vec if query_vec is not None else np.zeros(len(self.index.chunks))
        if mode == "dense":
            order = np.argsort(-cos)
            hits = [Hit(self.index.chunks[i], float(cos[i]), float(cos[i])) for i in order if cos[i] >= min_score]
            return hits[:k]

        bm = np.asarray(self.bm25.scores(tokenize(query_text)))
        if mode == "bm25":
            order = np.argsort(-bm)
            return [Hit(self.index.chunks[i], float(bm[i]), float(cos[i])) for i in order[:k] if bm[i] > 0]

        fused: dict[int, float] = {}
        for ranking in (np.argsort(-cos)[:POOL], [i for i in np.argsort(-bm)[:POOL] if bm[i] > 0]):
            for rank, i in enumerate(ranking):
                fused[int(i)] = fused.get(int(i), 0.0) + 1.0 / (RRF_K + rank + 1)
        order = sorted(fused, key=lambda i: -fused[i])
        hits = [Hit(self.index.chunks[i], fused[i], float(cos[i])) for i in order if cos[i] >= min_score]
        return hits[:k]


def top_docs(hits: list[Hit], n: int) -> list[Hit]:
    """Best chunk per document, in rank order — what the agent and the doc-level metrics use."""
    seen: set[str] = set()
    out: list[Hit] = []
    for h in hits:
        if h.chunk.doc_id not in seen:
            seen.add(h.chunk.doc_id)
            out.append(h)
        if len(out) == n:
            break
    return out
