# ScamShield TH

An LLM agent that tells Thai users whether an SMS, LINE or email message is a scam. Paste a message (or a
screenshot) and it returns a validated verdict — scam type, risk level, red flags quoted from the message,
recommended actions — with citations to official Thai warnings.

Capstone for *Building LLM-Powered Applications* (KMITL). All LLM calls go through the class proxy
(`gemma-4-E4B-it` for chat and vision, `bge-m3` for embeddings), from the backend only.

## Results (held-out test set: 35 real messages — 23 scam, 12 genuine)

| System | Scams caught | Genuine flagged | Flag precision | Flag F1 | Type accuracy | Type macro-F1 |
|---|---|---|---|---|---|---|
| **Baseline** — zero-shot gemma, no tools, no retrieval | 23/23 | 4/12 | 0.852 | 0.920 | 0.743 | 0.648 |
| Agent, no RAG (URL / indicator tools + brand–link precheck) | 23/23 | **2/12** | **0.920** | **0.958** | **0.771** | 0.691 |
| **Agent + RAG** (what the app runs) | 23/23 | 3/12 | 0.885 | 0.939 | 0.743 | **0.692** |

"Flagged" = risk medium or high, i.e. what the user sees as a warning. Before the fixes described below, the agent
flagged **17 of 19** genuine messages (v1, `backend/eval/results/v1/`). With 35 messages, one message is ~3–8
points: read the counts, not just the ratios. The baseline also had one unparseable verdict (counted as not flagged).

The test set grew from 27 to 35 with 8 messages collected after all tuning (`"batch": 2`). On the original 27 the flag
counts reproduced exactly (3 / 1 / 2 genuine flagged); type accuracy moved by at most one message between runs. The
new 8 lowered type accuracy for the RAG agent (4/8): it is the deployed variant, but on this set the no-RAG agent is
as good or better on every metric — reported as found, not re-tuned on test.

**Retrieval** (query = raw message, document-level, test split):

| Setting | Recall@3 | MRR | Genuine messages that retrieve any warning |
|---|---|---|---|
| Dense, no score gate (naive default) | 0.696 | 0.616 | 100 % |
| **Dense, `min_score` 0.40** (chosen on dev) | 0.696 | 0.616 | **92 %** |
| Dense, `min_score` 0.45 (previous default) | 0.652 | 0.573 | 92 % |
| Hybrid BM25 + RRF, `min_score` 0.40 (app default) | 0.609 | 0.557 | 92 % |

Hybrid beat dense on the dev split (R@3 0.773 vs 0.591), tied on the first 27 test messages, and loses on the full
35 (0.609 vs 0.696) — reported as found; the default was chosen on dev and is not switched on test.

**Method.** The 53 real messages (`data/messages/real.jsonl`, from the author's phone, PII redacted) were first
scored as v1, which exposed the false positives. To fix them without contaminating the score, the set was split once
(seeded, stratified): every prompt change, brand-list entry and retrieval knob was chosen on `dev.jsonl`; `test.jsonl`
was scored once at the end.

**Known failures.** A genuine insurance-claim SMS with an unknown `.cc` link that asks for ID digits is flagged
high; a genuine loan-contract SMS is flagged once loan-scam advisories are retrieved; a genuine Amazon sign-in code
(`amazon.co.jp`) is flagged by all three systems because Amazon is not in `brands.csv`; gambling ads written with
look-alike characters (`ถoนไว`, `llตกง่าย`) are still flagged but typed as prize, phishing or investment. Details in the report.

## Architecture

```mermaid
flowchart LR
    U[Browser<br/>Next.js UI] -- "POST /api/scan · SSE" --> R
    U -- "POST /api/extract-text" --> R
    subgraph Backend[FastAPI backend]
        R[Router<br/>validation, status codes] --> S[ScanService<br/>SSE events]
        R --> X[ExtractService<br/>screenshot → text]
        S --> P[Precheck<br/>brand named ↔ link owner]
        S --> A[Agent loop<br/>native tools, max 6 steps,<br/>duplicate-call guard]
        A --> T1[inspect_url<br/>lookalike, homoglyph,<br/>.go.th/.co.th trust]
        A --> T2[check_indicator<br/>SQLite, SELECT-only]
        A --> T3[search_advisories<br/>bge-m3 + BM25, RRF,<br/>min_score gate]
        A --> V[Verdict<br/>JSON → Pydantic →<br/>repair ≤ 2, guardrails]
    end
    T2 --> D1[(indicators.sqlite)]
    T3 --> D2[(advisory index)]
    A & V & X -- OPENAI_API_KEY --> L[Class proxy<br/>gemma-4-E4B-it · bge-m3]
```

- **Router → service → repository**: `app/api` (HTTP only) → `app/services` + `app/agent` → `app/repositories`
  (indicators, advisories, brands).
- **Structured output**: the proxy ignores `response_format`, so the verdict is prompted as JSON, parsed, validated by
  Pydantic (including cross-field rules: genuine ⇔ low risk; medium/high needs a red flag) and repaired at most twice.
  Red-flag quotes that are not verbatim in the message are dropped.
- **Guardrails in code**: hard tool evidence (lookalike or mixed-script domain, reported indicator) forces risk = high;
  citations come only from the retrieval trail and only back a warning; the user message is delimited as data.
- **Tools are allow-listed** and their arguments validated; `inspect_url` never fetches the page.

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
pnpm dev                                  # http://localhost:3000
```

## Data
| Path | What | Committed |
|---|---|---|
| `data/advisories/` | 26 official scam warnings: `sources.csv` (URLs), `raw/*.txt`, `advisories.jsonl` (metadata) | yes |
| `data/messages/` | 61 real messages (`real.jsonl`) split into `dev.jsonl` (tuning) and `test.jsonl` (reported) | yes |
| `data/indicators/` | `seed.csv` official domains + hotlines, `brands.csv` brand names ↔ official domains | yes |
| `data/index/` | vector index + SQLite, rebuilt by `scripts.build_index` | no (generated) |

Re-download the corpus with `uv run --group fetch python -m scripts.fetch_advisories` (pages change; the committed
text is what the numbers were measured on).

## Reproducing the numbers
```bash
cd backend
uv run python -m eval.run_eval --split test --mode baseline      # zero-shot gemma, no tools, no retrieval
uv run python -m eval.run_eval --split test --mode agent_norag   # + inspect_url / check_indicator / precheck
uv run python -m eval.run_eval --split test --mode agent         # + search_advisories (RAG)
uv run python -m eval.run_retrieval --split test [--size 300]    # dense vs BM25 vs hybrid, min_score sweep
```
On Windows, set `PYTHONIOENCODING=utf-8` when redirecting the output to a file.
All runs use `temperature=0`; the proxy is not perfectly deterministic, so a rerun can move a message or two.
The proxy caps tokens per short window — the eval waits and retries on HTTP 429. Per-item results and logs are in
`backend/eval/results/`.

## Limitations
- 61 labelled messages from one person's phone; some labels rest on the recipient's judgement (`label_basis`).
- No database of reported scam numbers/links yet — `check_indicator` knows official channels only.
- `brands.csv` covers 30 brands; a genuine message from an unlisted brand on an unknown domain is judged on content alone.
- Screenshot reading (gemma vision) misreads some Thai words, so the text is shown for review before scanning.
