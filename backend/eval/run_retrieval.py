"""Retrieval eval: dense vs BM25 vs hybrid, and the min_score gate.

    uv run python -m eval.run_retrieval --split test
    uv run python -m eval.run_retrieval --split test --size 300   # also compare a chunk size (builds a temp index)

Query = the raw message (what a user pastes). A document is relevant when the message's `relevant_docs`
lists it; if that field is absent, any advisory tagged with the message's gold scam_type counts.
Metrics (document level, best chunk per doc):
  recall@k  — share of scam messages with at least one relevant advisory in the top k
  MRR       — mean of 1/rank of the first relevant advisory (0 if none in the top 10)
  legit-hit — share of genuine messages that retrieve ANY advisory (lower is better: nothing to cite)
Results go to eval/results/retrieval-<split>.json.
"""

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np
from openai import OpenAI

from app.config import get_settings
from app.rag.embed import embed_texts
from app.rag.hybrid import Retriever, top_docs
from app.rag.store import Index
from app.repositories.advisories import AdvisoryRepository

RESULTS_DIR = Path(__file__).parent / "results"
GATES = [0.0, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]


def relevant(item: dict, doc_types: dict[str, set[str]]) -> set[str]:
    if item.get("relevant_docs"):
        return set(item["relevant_docs"])
    return {d for d, types in doc_types.items() if item["scam_type"] in types}


def evaluate(retriever: Retriever, items: list[dict], vecs: np.ndarray, doc_types: dict[str, set[str]],
             mode: str, gate: float) -> dict:
    rec3 = rec5 = rr = 0.0
    n_scam = legit_hits = n_legit = 0
    for it, v in zip(items, vecs):
        docs = [h.chunk.doc_id for h in top_docs(
            retriever.search(v, it["message"], mode=mode, k=50, min_score=gate), 10)]
        if it["is_scam"]:
            rel = relevant(it, doc_types)
            if not rel:
                continue  # no advisory of this type in the corpus: retrieval can't be scored
            n_scam += 1
            ranks = [i for i, d in enumerate(docs, 1) if d in rel]
            rec3 += bool(ranks and ranks[0] <= 3)
            rec5 += bool(ranks and ranks[0] <= 5)
            rr += 1 / ranks[0] if ranks else 0.0
        else:
            n_legit += 1
            legit_hits += bool(docs[:3])
    return {
        "mode": mode, "min_score": gate, "n_scam": n_scam, "n_legit": n_legit,
        "recall@3": rec3 / n_scam if n_scam else None,
        "recall@5": rec5 / n_scam if n_scam else None,
        "mrr": rr / n_scam if n_scam else None,
        "legit_hit": legit_hits / n_legit if n_legit else None,
    }


def fmt(x: float | None) -> str:
    return "  -  " if x is None else f"{x:.3f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--size", type=int, help="also evaluate an index rebuilt with this chunk size")
    ap.add_argument("--include-review", action="store_true")
    a = ap.parse_args()

    s = get_settings()
    repo = AdvisoryRepository(s.data_dir)
    doc_types = {d["id"]: set(d["scam_types"]) for d in repo.documents()}
    path = s.data_dir / "messages" / f"{a.split}.jsonl"
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    skipped = [it["id"] for it in items if it.get("needs_review") and not a.include_review]
    items = [it for it in items if it["id"] not in skipped]  # unconfirmed labels are not scored
    if skipped:
        print(f"skipping {len(skipped)} needs_review items (use --include-review): {', '.join(skipped)}")
    client = OpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url)
    vecs = embed_texts(client, s.embed_model, [it["message"] for it in items])

    indexes = {f"size={Index.load(repo.index_dir).meta['chunk_size']}": repo.retriever()}
    if a.size:
        from scripts.build_index import build
        with tempfile.TemporaryDirectory() as tmp:
            indexes[f"size={a.size}"] = Retriever(build(a.size, 1, Path(tmp)))

    rows = []
    print(f"[{a.split}] {len(items)} messages")
    print(f"{'index':10} {'mode':7} {'gate':>5}  {'R@3':>6} {'R@5':>6} {'MRR':>6} {'legit-hit':>9}")
    for name, retriever in indexes.items():
        for mode in ("dense", "bm25", "hybrid"):
            for gate in (GATES if mode != "bm25" else [0.0]):
                r = evaluate(retriever, items, vecs, doc_types, mode, gate) | {"index": name}
                rows.append(r)
                print(f"{name:10} {mode:7} {gate:5.2f}  {fmt(r['recall@3']):>6} {fmt(r['recall@5']):>6} "
                      f"{fmt(r['mrr']):>6} {fmt(r['legit_hit']):>9}")
    print(f"(n_scam scored={rows[0]['n_scam']}, n_legit={rows[0]['n_legit']})")

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"retrieval-{a.split}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
