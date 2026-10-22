"""Offline RAG tests: chunking, Thai BM25, fusion and the min_score gate (no embeddings calls)."""

import numpy as np

from app.rag.bm25 import BM25, tokenize
from app.rag.chunk import chunk_text
from app.rag.hybrid import Retriever, top_docs
from app.rag.store import Index, StoredChunk


def test_chunks_respect_size_and_keep_text():
    text = "\n".join(f"ย่อหน้าที่ {i} " + "ข้อความเตือนภัย " * 20 for i in range(10))
    chunks = chunk_text("doc", text, size=300, overlap=1)
    assert len(chunks) > 3
    assert all(len(c.text) <= 300 for c in chunks)
    assert all(c.id.startswith("doc#") for c in chunks)
    assert any("ย่อหน้าที่ 9" in c.text for c in chunks[-3:])  # nothing dropped at the end


def test_thai_tokenizer_splits_words():
    toks = tokenize("พัสดุตกค้างกรุณาชำระเงิน")
    assert "พัสดุ" in toks and len(toks) >= 3


def test_bm25_prefers_matching_doc():
    bm = BM25([tokenize("หลอกให้กู้เงินออนไลน์"), tokenize("พัสดุตกค้าง ไปรษณีย์")])
    s = bm.scores(tokenize("SMS พัสดุตกค้าง"))
    assert s[1] > s[0]


def _index() -> Index:
    chunks = [
        StoredChunk("a#0", "a", "พัสดุตกค้าง ชำระค่าธรรมเนียม", "parcel", "src", "u1"),
        StoredChunk("a#1", "a", "ไปรษณีย์ไทย ไม่ส่ง SMS ให้ชำระเงิน", "parcel", "src", "u1"),
        StoredChunk("b#0", "b", "แอปเงินกู้เถื่อน อนุมัติด่วน", "loan", "src", "u2"),
    ]
    vecs = np.array([[1, 0], [0.9, 0.436], [0, 1]], dtype=np.float32)
    return Index(chunks, vecs / np.linalg.norm(vecs, axis=1, keepdims=True), {})


def test_min_score_gate_drops_unrelated():
    r = Retriever(_index())
    q = np.array([1.0, 0.0], dtype=np.float32)
    assert {h.chunk.doc_id for h in r.search(q, "x", mode="dense", k=5, min_score=0.5)} == {"a"}
    assert len(r.search(q, "x", mode="dense", k=5, min_score=0.0)) == 3


def test_hybrid_and_top_docs_dedupe():
    r = Retriever(_index())
    hits = r.search(np.array([1.0, 0.0], dtype=np.float32), "พัสดุตกค้าง", mode="hybrid", k=5, min_score=0.0)
    assert hits[0].chunk.doc_id == "a"
    assert [h.chunk.doc_id for h in top_docs(hits, 5)] == ["a", "b"]
