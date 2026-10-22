"""Deterministic message precheck, run in code before the model judges anything.

Finds every link in the message and asks one question a careful person would: does the link belong to the
sender the message claims to be? "Claims AIS, links to m.ais.co.th" is evidence of a genuine message;
"claims Bangkok Bank, links to kusor.cn" is evidence of a scam. Without this the model sees only "there is a
link" — which genuine brand SMS also have — and over-flags.
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from app.agent.tools import SHORTENERS, registrable, thai_tld_trust
from app.repositories.brands import Brand, BrandRepository

# http(s) URLs, www. hosts and bare "name.tld/path" hosts; e-mail addresses are skipped by the lookbehind.
URL_RE = re.compile(
    r"(?<![@\w.])((?:https?://)?(?:www\.)?(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,24}(?:/[^\s\"'<>()]*)?)",
    re.IGNORECASE,
)


@dataclass
class Precheck:
    links: list[dict] = field(default_factory=list)
    claimed: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)  # English lines for the verdict prompt
    consistent: bool = False  # a claimed brand's own domain is linked (or no link at all)


def find_hosts(message: str) -> list[str]:
    hosts = []
    for m in URL_RE.finditer(message):
        raw = m.group(1)
        host = (urlsplit(raw if "://" in raw else "http://" + raw).hostname or "").lower().removeprefix("www.")
        if host and "." in host and host not in hosts and not host.replace(".", "").isdigit():
            hosts.append(host)
    return hosts


def precheck(message: str, brands: BrandRepository) -> Precheck:
    out = Precheck()
    claimed: list[Brand] = brands.mentioned_in(message)
    out.claimed = [b.name for b in claimed]
    for host in find_hosts(message):
        owner = brands.owner_of(host)
        kind = ("official" if owner else "vetted Thai organisation" if thai_tld_trust(host)
                else "URL shortener" if registrable(host) in SHORTENERS else "unknown")
        out.links.append({"host": host, "kind": kind, "owner": owner.name if owner else None})

    if not out.links:
        out.evidence.append("The message contains no link.")
        out.consistent = True
        return out
    for link in out.links:
        out.evidence.append(f"Link {link['host']}: {link['kind']}" + (f" (belongs to {link['owner']})" if link["owner"] else ""))
    if claimed:
        names = ", ".join(out.claimed)
        own = [link for link in out.links if link["owner"] in out.claimed]
        if own:
            out.consistent = True
            out.evidence.append(f"CONSISTENT: the message names {names} and links to that brand's own domain "
                                f"({own[0]['host']}) — typical of a genuine message unless it asks for something risky.")
        else:
            out.evidence.append(f"MISMATCH: the message names {names} but none of its links belong to "
                                f"{'that brand' if len(claimed) == 1 else 'those brands'} — typical of impersonation.")
        return out
    # No brand named: the sender is whoever owns the links. Official links (plus at most a shortener, as real
    # senders often add a bit.ly "read more") point to a genuine sender.
    owners = {link["owner"] for link in out.links if link["owner"]}
    others = [link for link in out.links if not link["owner"] and link["kind"] != "URL shortener"]
    if len(owners) == 1 and not others:
        out.consistent = True
        extra = (" An extra URL shortener next to the official link (e.g. a bit.ly 'read more') is common in "
                 "genuine messages." if len(out.links) > 1 else "")
        out.evidence.append(f"CONSISTENT: no brand is named and the link goes to {owners.pop()}'s own domain — "
                            f"typical of a genuine message unless it asks for something risky.{extra}")
    return out
