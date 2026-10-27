# Labelled messages

One JSON object per line. Fields: `id`, `split`, `channel`, `message`, `is_scam`, `scam_type`, `risk_level`, `source`, `note`.

| File | Use | Rule |
|---|---|---|
| `real.jsonl` | all 61 real messages (PII redacted) | source of the split below; the first 53 were scored once as "v1" |
| `dev.jsonl` | 9 synthetic + 26 real — prompt iteration, knob choice | may be looked at and tuned on freely |
| `test.jsonl` | 35 real (27 from the split + 8 batch-2) — the reported numbers | never used to write prompts, brand lists or pick knobs |

The split is made by `backend/scripts/split_messages.py` (seeded, stratified by scam_type). Messages collected later
carry `"batch": 2` and go straight to test (never seen during tuning). The split exists because the
v1 run on all real messages was used to diagnose false positives; see `backend/eval/results/v1/README.md`.
Labels marked `label_basis: "user judgement"` come from the person who received the message, not from a domain check.

## What test.jsonl needs (target ≥ 30, aim 40)
- Real messages only (your phone, family, friends) — never generated, never copied from `data/advisories/`.
- About 60 % scam / 40 % genuine. Genuine messages **with links** (bank, courier, shop) are essential: a set where
  every scam has a link and no genuine message does makes link-spotting look like intelligence.
- Optional `relevant_docs`: advisory ids that match the message; otherwise relevance falls back to `scam_type`.
- `needs_review: true` marks a label someone still has to confirm.

## Labelling rules
- `scam_type`: pick the sector being impersonated or the lure (`fake_parcel`, `fake_bank_or_loan`, `gov_impersonation`,
  `job_task`, `investment`, `romance`, `prize_lottery`, `gambling`). Use `phishing_link` only when a credential-stealing link has no
  clearer sector. `legit` = a genuine message. `other` = a scam that fits none of the above.
- `risk_level`: `legit` ⇒ `low`; any scam type ⇒ `medium` or `high`.
- Remove personal data (names, real phone numbers, account numbers) from real messages before committing.
