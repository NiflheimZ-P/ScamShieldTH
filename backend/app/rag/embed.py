"""bge-m3 embeddings through the class proxy (1024-dim, multilingual — handles Thai)."""

import numpy as np
from openai import AsyncOpenAI, OpenAI

BATCH = 32


def _normalise(vecs: list[list[float]]) -> np.ndarray:
    m = np.asarray(vecs, dtype=np.float32)
    return m / np.clip(np.linalg.norm(m, axis=1, keepdims=True), 1e-12, None)  # cosine = dot product


def embed_texts(client: OpenAI, model: str, texts: list[str]) -> np.ndarray:
    """Sync, batched — used by the offline index build and the eval."""
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        r = client.embeddings.create(model=model, input=texts[i : i + BATCH])
        out.extend(d.embedding for d in sorted(r.data, key=lambda d: d.index))
    return _normalise(out)


async def embed_query(client: AsyncOpenAI, model: str, text: str) -> np.ndarray:
    r = await client.embeddings.create(model=model, input=[text])
    return _normalise([r.data[0].embedding])[0]
