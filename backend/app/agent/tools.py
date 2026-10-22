"""Agent tools: JSON specs for native `tools=`, argument validation, and the implementations.

Only names in TOOLS can run. Arguments come from the model, so each tool validates them with a
Pydantic model and returns an error string (never raises) — the loop feeds that back to the model.
`search_advisories` joins the allow-list only when the RAG index exists (see app/rag).
"""

import ipaddress
import json
import re
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit

from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

from app.rag.embed import embed_query
from app.rag.hybrid import Mode, Retriever, top_docs
from app.repositories.indicators import Indicator, IndicatorRepository


@dataclass(frozen=True)
class ToolResult:
    content: str  # what the model reads (JSON text)
    summary: str  # one Thai line for the UI trace
    tone: Literal["warn", "ok", "info"]
    # Thai one-liners for evidence strong enough that the verdict must be high risk
    # (lookalike of an official domain, mixed-script host, reported indicator). See verdict.apply_evidence_floor.
    strong: tuple[str, ...] = field(default=())
    # {title, source, url} of advisories this call retrieved — the only source of Verdict.citations.
    citations: tuple[dict, ...] = field(default=())


# ---------- check_indicator ----------

class CheckIndicatorArgs(BaseModel):
    kind: Literal["phone", "domain", "line_id", "bank_account"]
    value: str = Field(min_length=1, max_length=200)


KIND_TH = {"phone": "เบอร์", "domain": "โดเมน", "line_id": "LINE ID", "bank_account": "บัญชี"}


def check_indicator(repo: IndicatorRepository, args: CheckIndicatorArgs) -> ToolResult:
    hits = repo.lookup(args.kind, args.value)
    reported = [h for h in hits if h.status == "reported"]
    official = [h for h in hits if h.status == "official"]
    label = f"{KIND_TH[args.kind]} {args.value}"
    if reported:
        summary, tone = f"{label} อยู่ในรายการที่ถูกแจ้งว่าเป็นมิจฉาชีพ ({reported[0].source})", "warn"
    elif official:
        summary, tone = f"{label} เป็นช่องทางทางการของ {official[0].label}", "ok"
    else:
        summary, tone = f"ไม่พบ{label}ในฐานข้อมูล (ไม่ได้แปลว่าปลอดภัย)", "info"
    content = {
        "kind": args.kind,
        "value": args.value,
        "found": bool(hits),
        "matches": [{"status": h.status, "label": h.label, "source": h.source} for h in hits],
        "note": "not found means no record, NOT that it is safe",
    }
    strong = tuple(f"{label} ถูกแจ้งว่าเป็นของมิจฉาชีพ ({h.source})" for h in reported)
    return ToolResult(json.dumps(content, ensure_ascii=False), summary, tone, strong)


# ---------- inspect_url (pure Python, never touches the network) ----------

class InspectUrlArgs(BaseModel):
    url: str = Field(min_length=3, max_length=2000)


SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "shorturl.at", "rb.gy", "is.gd", "s.id",
    "t.ly", "ow.ly", "tiny.cc", "goo.gl", "lin.ee",
}
RISKY_TLDS = {"cc", "top", "xyz", "vip", "icu", "shop", "online", "site", "live", "club", "buzz", "info", "cn"}
LURE_WORDS = {"verify", "secure", "security", "update", "login", "signin", "account", "refund", "confirm",
              "tracking", "support", "service", "kyc", "unlock"}
# Brand tokens -> what they impersonate. Matched against dash/dot-separated labels of the host.
BRAND_TOKENS = {
    "thailandpost": "ไปรษณีย์ไทย", "thpost": "ไปรษณีย์ไทย", "kbank": "KBank", "kasikorn": "KBank",
    "kasikornbank": "KBank", "scb": "SCB", "krungthai": "กรุงไทย", "ktb": "กรุงไทย",
    "bangkokbank": "ธนาคารกรุงเทพ", "bbl": "ธนาคารกรุงเทพ", "krungsri": "กรุงศรี", "gsb": "ออมสิน",
    "pea": "PEA", "mea": "MEA", "bot": "ธปท.", "ais": "AIS", "shopee": "Shopee", "lazada": "Lazada",
    "flash": "Flash Express", "kerry": "Kerry", "line": "LINE", "steam": "Steam", "paypal": "PayPal",
    "facebook": "Facebook", "apple": "Apple", "netflix": "Netflix", "microsoft": "Microsoft",
}
SECOND_LEVEL = {"co", "or", "go", "ac", "in", "mi", "net", "com"}
# Cyrillic/Greek letters that render like Latin ones (the common homoglyph set, not all of Unicode).
CONFUSABLES = str.maketrans("аеорсхуіјѕԁɡονρτ", "aeopcxyijsdgovpt")


def registrable(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in SECOND_LEVEL and len(parts[-1]) == 2:
        return ".".join(parts[-3:])  # e.g. thailandpost.co.th
    return ".".join(parts[-2:])


# Thai second-level domains with registrant checks by THNIC. Restricted ones can only be held by that kind of body;
# .co.th / .or.th need Thai company / organisation documents (verifiable owner, but not proof of good intent).
# .in.th is deliberately absent: open to individuals.
RESTRICTED_TLDS = {"go.th": "government", "ac.th": "education", "mi.th": "military"}
VETTED_TLDS = {"co.th": "company", "or.th": "organisation"}
TLD_TRUST_TH = {
    "government": "โดเมน .go.th จดได้เฉพาะหน่วยงานรัฐไทย",
    "education": "โดเมน .ac.th จดได้เฉพาะสถานศึกษาไทย",
    "military": "โดเมน .mi.th จดได้เฉพาะหน่วยงานทหารไทย",
    "company": "โดเมน .co.th ต้องจดด้วยเอกสารนิติบุคคลไทย (ตรวจสอบเจ้าของได้ แต่ไม่ได้รับรองว่าข้อความเป็นของจริง)",
    "organisation": "โดเมน .or.th ต้องจดด้วยเอกสารองค์กรไทย (ตรวจสอบเจ้าของได้ แต่ไม่ได้รับรองว่าข้อความเป็นของจริง)",
}
TLD_TRUST_EN = {
    "government": "restricted: only Thai government agencies can register .go.th",
    "education": "restricted: only Thai educational institutions can register .ac.th",
    "military": "restricted: only Thai military bodies can register .mi.th",
    "company": "vetted: .co.th requires Thai company registration documents (owner is traceable; "
               "not proof the message is genuine)",
    "organisation": "vetted: .or.th requires Thai organisation documents (owner is traceable; "
                    "not proof the message is genuine)",
}


def thai_tld_trust(host: str) -> str | None:
    suffix = ".".join(host.split(".")[-2:])
    return RESTRICTED_TLDS.get(suffix) or VETTED_TLDS.get(suffix)


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def mixed_script(host: str) -> bool:
    """A label mixing ASCII letters with non-ASCII letters (e.g. 'steamcoฟหกmmunity'). Whole-Thai labels
    such as genuine .ไทย domains are not mixed."""
    for label in host.split("."):
        has_ascii = any("a" <= ch <= "z" for ch in label)
        has_other = any(ord(ch) > 127 and ch.isalpha() for ch in label)
        if has_ascii and has_other:
            return True
    return False


def imitated(host: str, official: list[Indicator]) -> Indicator | None:
    """The official domain this host looks like, if any (and it isn't that domain)."""
    skeleton = "".join(ch for ch in host.translate(CONFUSABLES) if ord(ch) < 128)  # drop inserted junk
    skel_reg = registrable(skeleton)
    for o in official:
        if host == o.value or host.endswith("." + o.value):
            return None
    for o in official:
        name, cand = o.value.split(".")[0], skel_reg.split(".")[0]
        if skel_reg == o.value or skeleton.endswith("." + o.value):
            return o  # identical once homoglyphs / inserted characters are removed
        if len(name) >= 5 and 0 < edit_distance(cand, name) <= (1 if len(name) < 8 else 2):
            return o  # typosquat, e.g. kasikornbamk.com
    return None


def inspect_url(official: list[Indicator], args: InspectUrlArgs) -> ToolResult:
    raw = args.url.strip()
    parts = urlsplit(raw if re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.IGNORECASE) else "http://" + raw)
    host = (parts.hostname or "").lower().removeprefix("www.")
    if not host:
        return ToolResult(json.dumps({"error": "could not parse a host from url"}), "อ่าน URL ไม่ได้", "info")

    flags: list[str] = []
    strong: list[str] = []
    official_match = next((o for o in official if host == o.value or host.endswith("." + o.value)), None)
    reg = registrable(host)
    labels = re.split(r"[.\-]", host)
    tld_trust = thai_tld_trust(host)

    if mixed_script(host):
        flags.append("mixes Latin letters with Thai/other-script characters inside the domain — look-alike trick")
        strong.append(f"โดเมน {host} มีตัวอักษรต่างภาษาปนกันเพื่อเลียนแบบชื่อจริง")
    look = imitated(host, official)
    if look:
        flags.append(f"imitates the official domain {look.value} ({look.label}) but is a different domain")
        strong.append(f"โดเมน {host} เลียนแบบ {look.value} ของ {look.label}")

    if raw.lower().startswith("http://"):
        flags.append("uses plain http (no TLS)")
    if host.startswith("xn--") or ".xn--" in host:
        flags.append("punycode/IDN host — may imitate another name with look-alike letters")
    try:
        ipaddress.ip_address(host)
        flags.append("raw IP address instead of a domain")
    except ValueError:
        pass
    if reg in SHORTENERS:
        flags.append(f"URL shortener ({reg}) hides the real destination")
    if not official_match:
        brands = sorted({BRAND_TOKENS[t] for t in labels if t in BRAND_TOKENS})
        if brands and not look:
            flags.append(f"mentions {', '.join(brands)} but is not an official domain of that brand")
            strong.append(f"โดเมน {host} ใช้ชื่อ {', '.join(brands)} แต่ไม่ใช่โดเมนทางการ")
    if not official_match and tld_trust is None:
        # Name-shape heuristics only make sense for unvetted domains; a .go.th or .co.th name was vetted by THNIC.
        lures = sorted(LURE_WORDS.intersection(labels))
        if lures:
            flags.append(f"lure words in the domain: {', '.join(lures)}")
        if host.count("-") >= 2:
            flags.append("many hyphens in the domain")
        if host.rsplit(".", 1)[-1] in RISKY_TLDS:
            flags.append(f"TLD .{host.rsplit('.', 1)[-1]} is common in scam campaigns")

    if official_match and not flags:
        summary, tone = f"{host} เป็นโดเมนทางการของ {official_match.label} (แต่ลิงก์ที่แสดงอาจไม่ใช่ปลายทางจริง)", "ok"
    elif tld_trust and not flags:
        summary, tone = f"{host}: {TLD_TRUST_TH[tld_trust]}", "ok"
    elif flags:
        summary, tone = f"{host}: พบสัญญาณน่าสงสัย {len(flags)} ข้อ", "warn"
    else:
        summary, tone = f"{host}: ไม่พบสัญญาณผิดปกติจากโครงสร้าง URL (ไม่ได้ยืนยันว่าปลอดภัย)", "info"
    content = {
        "host": host,
        "registrable_domain": reg,
        "official_owner": official_match.label if official_match else None,
        "domain_trust": TLD_TRUST_EN.get(tld_trust or "", "unvetted: anyone can register this kind of domain"),
        "flags": flags,
        "strong_evidence": bool(strong),
        "note": "Only the visible text was checked. An official domain does not make the message safe: "
                "chat apps can show one address and open another, and scammers abuse real sites. "
                "Judge the request itself (unsolicited gift/prize, login, payment).",
    }
    return ToolResult(json.dumps(content, ensure_ascii=False), summary, tone, tuple(strong))


# ---------- registry ----------

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "inspect_url",
            "description": "Analyse the structure of a URL found in the message: lookalike brand names, "
                           "URL shorteners, punycode, plain http, risky TLDs, and whether it is an official domain. "
                           "Does not visit the site.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The URL exactly as written in the message"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_indicator",
            "description": "Look up a phone number, domain, LINE ID or bank account in the database of "
                           "official channels and reported scam indicators.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["phone", "domain", "line_id", "bank_account"]},
                    "value": {"type": "string", "description": "The value exactly as written in the message"},
                },
                "required": ["kind", "value"],
            },
        },
    },
]

SEARCH_SPEC = {
    "type": "function",
    "function": {
        "name": "search_advisories",
        "description": "Search official Thai scam warnings (Bank of Thailand, Cyber Police, Revenue Dept, PEA, "
                       "Thailand Post, SEC, banks ...) for advisories matching what the message claims or asks.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "Short Thai description of the scam pattern, e.g. "
                                         "'SMS แจ้งพัสดุตกค้าง ให้ชำระค่าธรรมเนียมผ่านลิงก์'"},
            },
            "required": ["query"],
        },
    },
}


class SearchAdvisoriesArgs(BaseModel):
    query: str = Field(min_length=2, max_length=300)


@dataclass(frozen=True)
class SearchConfig:
    retriever: Retriever
    client: AsyncOpenAI
    embed_model: str
    mode: Mode
    min_score: float
    n_docs: int = 3


async def search_advisories(cfg: SearchConfig, args: SearchAdvisoriesArgs) -> ToolResult:
    vec = None if cfg.mode == "bm25" else await embed_query(cfg.client, cfg.embed_model, args.query)
    hits = top_docs(cfg.retriever.search(vec, args.query, mode=cfg.mode, k=20, min_score=cfg.min_score), cfg.n_docs)
    if not hits:
        content = {"results": [], "note": "no advisory is similar enough to this query"}
        return ToolResult(json.dumps(content, ensure_ascii=False), "ไม่พบคำเตือนทางการที่ตรงกับข้อความนี้", "info")
    results = [
        {"n": i, "title": h.chunk.title, "source": h.chunk.source, "excerpt": h.chunk.text[:700]}
        for i, h in enumerate(hits, 1)
    ]
    cites = tuple({"title": h.chunk.title, "source": h.chunk.source, "url": h.chunk.url} for h in hits)
    summary = f"พบคำเตือนที่เกี่ยวข้อง {len(hits)} รายการ เช่น “{hits[0].chunk.title[:50]}”"
    return ToolResult(json.dumps({"results": results}, ensure_ascii=False), summary, "info", citations=cites)


ARG_MODELS: dict[str, type[BaseModel]] = {
    "inspect_url": InspectUrlArgs,
    "check_indicator": CheckIndicatorArgs,
    "search_advisories": SearchAdvisoriesArgs,
}


class Toolbox:
    """Allow-listed dispatch. Unknown tools and bad arguments come back as error results.
    `search_advisories` is offered only when a search config (i.e. a built index) is given."""

    def __init__(self, repo: IndicatorRepository, search: SearchConfig | None = None):
        self._repo = repo
        self._official = repo.official_domains()
        self._search = search
        self.specs = [*TOOL_SPECS, SEARCH_SPEC] if search else list(TOOL_SPECS)

    async def run(self, name: str, raw_args: dict) -> ToolResult:
        model = ARG_MODELS.get(name)
        if model is None or (name == "search_advisories" and self._search is None):
            return ToolResult(json.dumps({"error": f"unknown tool {name!r}"}), f"ไม่รู้จักเครื่องมือ {name}", "info")
        try:
            args = model.model_validate(raw_args)
        except ValidationError as e:
            msg = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
            return ToolResult(json.dumps({"error": f"invalid arguments: {msg}"}), "อาร์กิวเมนต์ไม่ถูกต้อง", "info")
        if name == "inspect_url":
            return inspect_url(self._official, args)
        if name == "search_advisories":
            return await search_advisories(self._search, args)
        return check_indicator(self._repo, args)
