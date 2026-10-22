"""One-off, reproducible split of the real messages into a tuning half and a held-out half.

    uv run python -m scripts.split_messages --source ../data/messages/real.jsonl

Why: v1 was scored on all real messages and exposed false positives on genuine messages with links. Fixing that
by looking at the same messages would make the re-test meaningless, so the real set is split once (seeded,
stratified by scam_type) — fixes are developed on `dev.jsonl` only and `test.jsonl` is scored once at the end.
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from app.config import get_settings

SEED = 20261023


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    a = ap.parse_args()

    msgs = get_settings().data_dir / "messages"
    real = [json.loads(line) for line in a.source.read_text(encoding="utf-8").splitlines() if line.strip()]
    synthetic = [json.loads(line) for line in (msgs / "dev.jsonl").read_text(encoding="utf-8").splitlines()
                 if line.strip() and json.loads(line)["id"].startswith("dev-0")]  # the 9 hand-made dev items

    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in real:
        by_type[r["scam_type"]].append(r)
    rng = random.Random(SEED)
    dev_real, test = [], []
    flip = False
    for t in sorted(by_type):
        group = by_type[t][:]
        rng.shuffle(group)
        half = len(group) // 2 + (len(group) % 2 if flip else 0)  # alternate who gets the odd one out
        flip = not flip
        test += group[:half]
        dev_real += group[half:]

    for r in dev_real:
        r["split"] = "dev"
    test.sort(key=lambda r: r["id"])
    dev_real.sort(key=lambda r: r["id"])
    (msgs / "dev.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in synthetic + dev_real),
                                    encoding="utf-8")
    (msgs / "test.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in test),
                                     encoding="utf-8")

    def counts(rows: list[dict]) -> str:
        return f"{len(rows)} (scam {sum(r['is_scam'] for r in rows)}, legit {sum(not r['is_scam'] for r in rows)})"
    print(f"dev  = {len(synthetic)} synthetic + {counts(dev_real)} real")
    print(f"test = {counts(test)}")


if __name__ == "__main__":
    main()
