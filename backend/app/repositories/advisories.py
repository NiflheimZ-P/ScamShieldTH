"""Repository: the advisory corpus (raw text + metadata) and its vector index."""

import json
from pathlib import Path

from app.rag.hybrid import Retriever
from app.rag.store import Index


class AdvisoryRepository:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "advisories"
        self.index_dir = data_dir / "index" / "advisories"

    def documents(self) -> list[dict]:
        """Metadata rows plus the committed raw text."""
        rows = []
        for line in (self.root / "advisories.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                m = json.loads(line)
                m["text"] = (self.root / "raw" / f"{m['id']}.txt").read_text(encoding="utf-8")
                rows.append(m)
        return rows

    def index_exists(self) -> bool:
        return (self.index_dir / "vectors.npy").exists()

    def retriever(self) -> Retriever:
        if not self.index_exists():
            raise FileNotFoundError(f"{self.index_dir} missing — run: uv run python -m scripts.build_index")
        return Retriever(Index.load(self.index_dir))
