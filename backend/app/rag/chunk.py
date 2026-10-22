"""Split advisory text into overlapping chunks on paragraph / sentence boundaries.

Thai has no spaces between words and few full stops, so we split on blank lines and newlines first,
then on spaces (Thai uses a space as a soft sentence break), and only hard-cut as a last resort.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    id: str  # "<doc_id>#<n>"
    doc_id: str
    text: str


def _pieces(text: str, size: int) -> list[str]:
    out: list[str] = []
    for para in re.split(r"\n+", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= size:
            out.append(para)
            continue
        buf = ""
        for part in re.split(r"(?<=\s)", para):  # keep the space on the left piece
            if len(buf) + len(part) > size and buf:
                out.append(buf.strip())
                buf = ""
            while len(part) > size:  # a single unbroken run longer than size
                out.append(part[:size])
                part = part[size:]
            buf += part
        if buf.strip():
            out.append(buf.strip())
    return out


def chunk_text(doc_id: str, text: str, size: int = 600, overlap: int = 1) -> list[Chunk]:
    """Greedy-pack pieces up to `size` chars; carry the last `overlap` pieces into the next chunk."""
    pieces = _pieces(text, size)
    chunks: list[Chunk] = []
    cur: list[str] = []
    for p in pieces:
        if cur and sum(len(x) + 1 for x in cur) + len(p) > size:
            chunks.append(Chunk(f"{doc_id}#{len(chunks)}", doc_id, "\n".join(cur)))
            cur = cur[-overlap:] if overlap else []
            if sum(len(x) + 1 for x in cur) + len(p) > size:
                cur = []
        cur.append(p)
    if cur:
        chunks.append(Chunk(f"{doc_id}#{len(chunks)}", doc_id, "\n".join(cur)))
    return chunks
