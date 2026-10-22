"""Download the advisory corpus listed in data/advisories/sources.csv.

    uv run --group fetch python -m scripts.fetch_advisories          # fetch missing pages
    uv run --group fetch python -m scripts.fetch_advisories --force  # re-fetch everything

Writes the main article text to data/advisories/raw/<id>.txt and metadata to
data/advisories/advisories.jsonl. Both are committed, so the index can be rebuilt without the network
(pages change or disappear; the committed text is what the eval numbers were measured on).
"""

import argparse
import csv
import json
import time
from datetime import date

import httpx
import trafilatura

from app.config import get_settings

MIN_CHARS = 400  # shorter than this is a cookie wall, a video page or a failed extract
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ScamShieldTH-coursework/0.1"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    root = get_settings().data_dir / "advisories"
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    meta_path = root / "advisories.jsonl"
    meta = {}
    if meta_path.exists():
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                m = json.loads(line)
                meta[m["id"]] = m

    with (root / "sources.csv").open(encoding="utf-8") as f:
        sources = list(csv.DictReader(f))

    ok = failed = 0
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as client:
        for src in sources:
            out = raw_dir / f"{src['id']}.txt"
            if out.exists() and src["id"] in meta and not a.force:
                ok += 1
                continue
            try:
                r = client.get(src["url"])
                r.raise_for_status()
                text = trafilatura.extract(r.text, include_comments=False, include_tables=False, favor_recall=True)
                info = trafilatura.extract_metadata(r.text)
            except Exception as e:  # noqa: BLE001 — network, HTTP or parse error: report and move on
                print(f"FAIL {src['id']}: {type(e).__name__}: {str(e)[:100]}")
                failed += 1
                continue
            if not text or len(text) < MIN_CHARS:
                print(f"SKIP {src['id']}: only {len(text or '')} chars extracted")
                failed += 1
                continue
            out.write_text(text, encoding="utf-8")
            meta[src["id"]] = {
                "id": src["id"],
                "url": src["url"],
                "source": src["source"],
                "title": (info.title if info and info.title else src["id"]).strip(),
                "published": info.date if info else None,
                "fetched": date.today().isoformat(),
                "scam_types": [t for t in src["scam_types"].split("|") if t],
                "chars": len(text),
            }
            print(f"OK   {src['id']}: {len(text)} chars — {meta[src['id']]['title'][:60]}")
            ok += 1
            time.sleep(1)  # be polite

    wanted = {s["id"] for s in sources}
    rows = [meta[k] for k in sorted(meta) if k in wanted]
    meta_path.write_text("".join(json.dumps(m, ensure_ascii=False) + "\n" for m in rows), encoding="utf-8")
    print(f"\n{ok} ok, {failed} failed -> {meta_path}")


if __name__ == "__main__":
    main()
