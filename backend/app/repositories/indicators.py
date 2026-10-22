"""Repository: phone / domain / LINE ID / bank-account lookups in SQLite.

The database is a generated artefact built from data/indicators/seed.csv (committed), so the
repo stays reproducible. Every query is a fixed SELECT with bind parameters and a LIMIT —
model-supplied values never become SQL text.
"""

import csv
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Kind = Literal["phone", "domain", "line_id", "bank_account"]
KINDS: tuple[str, ...] = ("phone", "domain", "line_id", "bank_account")

SCHEMA = """
CREATE TABLE indicators (
    kind   TEXT NOT NULL,
    value  TEXT NOT NULL,      -- normalised, see normalise()
    status TEXT NOT NULL CHECK (status IN ('official', 'reported')),
    label  TEXT NOT NULL,
    source TEXT NOT NULL
);
CREATE INDEX ix_indicators ON indicators (kind, value);
"""


@dataclass(frozen=True)
class Indicator:
    kind: str
    value: str
    status: str  # official | reported
    label: str
    source: str


def normalise(kind: str, value: str) -> str:
    v = value.strip().lower()
    if kind in ("phone", "bank_account"):
        v = re.sub(r"\D", "", v)
        if kind == "phone" and v.startswith("66") and len(v) == 11:
            v = "0" + v[2:]  # +66 81... -> 081...
    elif kind == "domain":
        v = re.sub(r"^[a-z]+://", "", v).split("/")[0].split(":")[0]
        v = v.removeprefix("www.")
    elif kind == "line_id":
        v = v.lstrip("@")
    return v


def build_db(csv_path: Path, db_path: Path) -> int:
    """(Re)build the SQLite file from the CSV. Returns the number of rows."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    with csv_path.open(encoding="utf-8") as f:
        rows = [
            (r["kind"], normalise(r["kind"], r["value"]), r["status"], r["label"], r["source"])
            for r in csv.DictReader(f)
            if r["kind"] in KINDS
        ]
    with sqlite3.connect(db_path) as con:
        con.executescript(SCHEMA)
        con.executemany("INSERT INTO indicators VALUES (?, ?, ?, ?, ?)", rows)
    return len(rows)


class IndicatorRepository:
    def __init__(self, db_path: Path, csv_path: Path | None = None):
        if not db_path.exists():
            if csv_path is None:
                raise FileNotFoundError(f"{db_path} missing — run scripts/seed_indicators.py")
            build_db(csv_path, db_path)
        self._db_path = db_path

    def _query(self, sql: str, params: tuple) -> list[Indicator]:
        # Read-only connection: even a bug here cannot write to the DB.
        uri = f"file:{self._db_path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as con:
            return [Indicator(*row) for row in con.execute(sql, params).fetchall()]

    def lookup(self, kind: str, value: str) -> list[Indicator]:
        if kind not in KINDS:
            raise ValueError(f"unknown kind {kind!r}")
        v = normalise(kind, value)
        if not v:
            return []
        return self._query(
            "SELECT kind, value, status, label, source FROM indicators "
            "WHERE kind = ? AND value = ? LIMIT 5",
            (kind, v),
        )

    def official_domains(self) -> list[Indicator]:
        return self._query(
            "SELECT kind, value, status, label, source FROM indicators "
            "WHERE kind = 'domain' AND status = 'official' LIMIT 500",
            (),
        )
