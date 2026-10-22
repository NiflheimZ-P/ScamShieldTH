# ScamShield TH

An LLM agent that tells Thai users whether an SMS, LINE or email message is a scam. It returns a
validated verdict (scam type, risk level, red flags, recommended actions), grounded in official Thai
advisories with citations.

> Work in progress — capstone for *Building LLM-Powered Applications* (KMITL).

## Architecture
```
frontend/  Next.js (TypeScript) UI — calls /api/*, rewritten to the backend
backend/   FastAPI: router → service (agent) → repositories; calls the class LLM proxy
data/      advisory corpus, labelled messages, indicator DB
```
The LLM (`gemma-4-E4B-it`) and embeddings (`bge-m3`) are reached only from the backend via the class proxy.

## Setup
Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+, pnpm.

```bash
cp backend/.env.example backend/.env          # backend only: put your course API key here
cp frontend/.env.example frontend/.env.local  # frontend: backend URL + mock switch (no secrets)

# backend
cd backend
uv sync
uv run python -m scripts.build_index      # chunk + embed the committed advisories (needs the proxy, ~1 min)
uv run uvicorn app.main:app --reload --port 8000
uv run pytest                             # offline tests, no proxy calls

# frontend (new terminal)
cd frontend
pnpm install
pnpm dev                      # http://localhost:3000
```

## Data
| Path | What | Committed |
|---|---|---|
| `data/advisories/` | 26 official scam warnings: `sources.csv` (URLs), `raw/*.txt`, `advisories.jsonl` (metadata) | yes |
| `data/messages/` | labelled messages: `dev.jsonl` (tuning) and `test.jsonl` (reported numbers) | yes |
| `data/indicators/seed.csv` | official domains and hotlines | yes |
| `data/index/` | vector index + SQLite, rebuilt by `scripts.build_index` | no (generated) |

Re-download the corpus with `uv run --group fetch python -m scripts.fetch_advisories` (pages change; the committed
text is what the numbers were measured on).

## Evaluation
```bash
cd backend
# classification: named baseline vs agent without / with RAG
uv run python -m eval.run_eval --split test --mode baseline      # zero-shot gemma, no tools, no retrieval
uv run python -m eval.run_eval --split test --mode agent_norag   # + inspect_url / check_indicator
uv run python -m eval.run_eval --split test --mode agent         # + search_advisories (RAG)
# retrieval: dense vs BM25 vs hybrid, min_score sweep, optional chunk-size comparison
uv run python -m eval.run_retrieval --split test [--size 300]
```
Metrics: scam-type accuracy and macro-F1; flagged (medium/high) precision / recall; retrieval recall@3/5, MRR and
legit-hit (share of genuine messages that retrieve any advisory). Results are written to `backend/eval/results/`.
