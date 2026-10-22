# Labelled messages

One JSON object per line. Fields: `id`, `split`, `channel`, `message`, `is_scam`, `scam_type`, `risk_level`, `source`, `note`.

| File | Use | Rule |
|---|---|---|
| `dev.jsonl` | prompt iteration, smoke tests | may be looked at and tuned on freely |
| `test.jsonl` | the reported numbers | real messages only; never used to write prompts or few-shot examples |

`dev.jsonl` is synthetic (drafted with Gemini, checked by a human). It is **not** used for any reported metric.

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
