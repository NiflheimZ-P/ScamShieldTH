# v1 results (2026-10-23) — before the dev/test split

Scored on all 53 real messages (`data/messages/real.jsonl`) with the code at commit d53dc4f.
They exposed false positives on genuine messages that contain links (baseline flagged 13/19, agent_norag 17/19).
The `agent` (RAG) run stopped at the proxy's 200k-token rate limit, so it has no file here.

Because these numbers were used to diagnose the problem, the real messages were then split once
(`scripts/split_messages.py`, seeded): fixes were developed on `dev.jsonl` only and the final numbers come from
the untouched `test.jsonl`. These v1 files are kept as the honest "before" for the report.
