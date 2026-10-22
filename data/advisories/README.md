# Advisory corpus

Official Thai scam warnings used for retrieval (RAG). Each row of `sources.csv` is one page:
`id, url, source, scam_types` — `source` names the issuing body, and "(ผ่าน X)" when the warning reached us
through a news outlet; `scam_types` uses the `ScamType` values and drives the default relevance labels in
`eval/run_retrieval.py`.

`scripts/fetch_advisories.py` downloads each page, extracts the main text with trafilatura and writes
`raw/<id>.txt` + `advisories.jsonl`. Pages that failed (403, 404, < 400 chars of text) were removed from the list.

Inclusion rule: the page must be a warning issued by a government agency, bank or carrier, or a news report that
quotes one. Text is kept for coursework retrieval only; the URL in every citation points back to the original.

Test messages are **not** taken from these pages, so retrieval is not scored on text it has already seen.
