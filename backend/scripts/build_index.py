"""Chunk the committed advisory text, embed with bge-m3 and write data/index/advisories/.

    uv run python -m scripts.build_index [--size 600] [--overlap 1] [--out DIR]

Also rebuilds the indicator SQLite file.
"""

import argparse
from pathlib import Path

from openai import OpenAI

from app.config import get_settings
from app.rag.chunk import chunk_text
from app.rag.embed import embed_texts
from app.rag.store import Index, StoredChunk
from app.repositories.advisories import AdvisoryRepository
from app.repositories.indicators import build_db


def build(size: int, overlap: int, out: Path | None = None) -> Index:
    s = get_settings()
    repo = AdvisoryRepository(s.data_dir)
    chunks: list[StoredChunk] = []
    for d in repo.documents():
        for c in chunk_text(d["id"], d["text"], size=size, overlap=overlap):
            chunks.append(StoredChunk(c.id, d["id"], c.text, d["title"], d["source"], d["url"]))
    client = OpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url)
    # Embed title + text: the title often names the scam type the body only describes.
    vectors = embed_texts(client, s.embed_model, [f"{c.title}\n{c.text}" for c in chunks])
    index = Index(chunks, vectors, {"model": s.embed_model, "chunk_size": size, "overlap": overlap,
                                    "n_docs": len({c.doc_id for c in chunks}), "n_chunks": len(chunks)})
    index.save(out or repo.index_dir)
    return index


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=600)
    ap.add_argument("--overlap", type=int, default=1)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    idx = build(a.size, a.overlap, a.out)
    print(f"index: {idx.meta}")
    s = get_settings()
    print(f"indicators: {build_db(s.indicators_csv, s.indicators_db)} rows")
