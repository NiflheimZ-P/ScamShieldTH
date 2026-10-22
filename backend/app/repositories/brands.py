"""Repository: brands people get SMS from, the words that name them, and their official domains.

Source of truth is data/indicators/brands.csv (committed, one evidence URL per row).
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Brand:
    name: str
    keywords: tuple[str, ...]
    domains: tuple[str, ...]

    def owns(self, host: str) -> bool:
        return any(host == d or host.endswith("." + d) for d in self.domains)


def _pattern(keyword: str) -> re.Pattern:
    k = re.escape(keyword.lower())
    # ASCII keywords need word boundaries ("ais" must not match "details"); Thai has no spaces, so plain match.
    return re.compile(rf"(?<![a-z0-9]){k}(?![a-z0-9])" if keyword.isascii() else k)


class BrandRepository:
    def __init__(self, csv_path: Path):
        with csv_path.open(encoding="utf-8") as f:
            self.brands = [
                Brand(r["brand"], tuple(k.strip() for k in r["keywords"].split("|") if k.strip()),
                      tuple(d.strip().lower() for d in r["domains"].split("|") if d.strip()))
                for r in csv.DictReader(f)
            ]
        self._patterns = [(b, [_pattern(k) for k in b.keywords]) for b in self.brands]

    def mentioned_in(self, text: str) -> list[Brand]:
        low = text.lower()
        return [b for b, pats in self._patterns if any(p.search(low) for p in pats)]

    def owner_of(self, host: str) -> Brand | None:
        return next((b for b in self.brands if b.owns(host)), None)
