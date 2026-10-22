"""Offline tests: tools, schema rules, JSON extraction. No proxy calls."""

import asyncio
import json

import pytest
from pydantic import ValidationError

from app.agent.tools import Toolbox
from app.agent.verdict import apply_evidence_floor, extract_json, ground_quotes
from app.api.schemas import Verdict
from app.config import get_settings
from app.repositories.indicators import IndicatorRepository, build_db, normalise


@pytest.fixture(scope="module")
def toolbox(tmp_path_factory) -> Toolbox:
    db = tmp_path_factory.mktemp("idx") / "indicators.sqlite"
    build_db(get_settings().indicators_csv, db)
    return Toolbox(IndicatorRepository(db))


def run(toolbox, name, args):
    return asyncio.run(toolbox.run(name, args))


def flags(toolbox, url):
    return json.loads(run(toolbox, "inspect_url", {"url": url}).content)


def test_lookalike_domain_flagged(toolbox):
    r = flags(toolbox, "https://thailandpost-tracking-update.com")
    assert r["official_owner"] is None
    assert any("ไปรษณีย์ไทย" in f for f in r["flags"])


def test_official_domain_ok(toolbox):
    res = run(toolbox, "inspect_url", {"url": "https://track.thailandpost.co.th/x"})
    assert res.tone == "ok"
    assert json.loads(res.content)["official_owner"] == "ไปรษณีย์ไทย"


def test_shortener_and_http(toolbox):
    assert any("shortener" in f for f in flags(toolbox, "https://bit.ly/3xyzJob")["flags"])
    assert any("http" in f for f in flags(toolbox, "http://kcyber-security-th.net")["flags"])


def test_mixed_script_and_lookalike_are_strong(toolbox):
    res = run(toolbox, "inspect_url", {"url": "steamcoฟหกmmunity.com/gift-card/pay/201"})
    assert res.strong and res.tone == "warn"
    assert run(toolbox, "inspect_url", {"url": "https://kasikornbamk.com/login"}).strong  # typosquat
    assert run(toolbox, "inspect_url", {"url": "https://steamcommunlty.com/gift"}).strong
    assert run(toolbox, "inspect_url", {"url": "https://ѕteamcommunity.com"}).strong  # Cyrillic ѕ


def test_official_and_thai_idn_not_strong(toolbox):
    assert not run(toolbox, "inspect_url", {"url": "https://steamcommunity.com/gift-card/pay/201"}).strong
    assert not run(toolbox, "inspect_url", {"url": "https://ไปรษณีย์ไทย.com"}).strong  # all-Thai label


def test_thai_tld_trust(toolbox):
    gov = run(toolbox, "inspect_url", {"url": "https://refund-service.rd.go.th/login"})
    assert gov.tone == "ok" and not json.loads(gov.content)["flags"]  # lure words ignored on .go.th
    assert json.loads(gov.content)["domain_trust"].startswith("restricted")
    co = json.loads(run(toolbox, "inspect_url", {"url": "https://example.co.th"}).content)
    assert co["domain_trust"].startswith("vetted")
    assert json.loads(run(toolbox, "inspect_url", {"url": "https://x.in.th"}).content)["domain_trust"].startswith("unvetted")
    # vetted TLD does not excuse brand impersonation
    assert run(toolbox, "inspect_url", {"url": "https://kbank-verify.co.th"}).strong


def test_evidence_floor_forces_high():
    v = Verdict.model_validate({**BASE, "scam_type": "legit", "risk_level": "low"})
    v = apply_evidence_floor(v, ["โดเมนเลียนแบบ"])
    assert (v.scam_type.value, v.risk_level.value) == ("phishing_link", "high")
    assert v.red_flags[0].text == "โดเมนเลียนแบบ"


def test_check_indicator_official_hotline(toolbox):
    res = run(toolbox, "check_indicator", {"kind": "phone", "value": "02-888-8888"})
    assert res.tone == "ok"


def test_check_indicator_unknown_is_not_safe(toolbox):
    res = run(toolbox, "check_indicator", {"kind": "line_id", "value": "@pea-refund99"})
    assert res.tone == "info"
    assert json.loads(res.content)["found"] is False


def test_unknown_tool_and_bad_args_are_errors_not_exceptions(toolbox):
    assert "error" in json.loads(run(toolbox, "rm_rf", {}).content)
    assert "error" in json.loads(run(toolbox, "check_indicator", {"kind": "sql", "value": "x"}).content)


def test_normalise():
    assert normalise("phone", "+66 81-234-5678") == "0812345678"
    assert normalise("domain", "https://www.KasikornBank.com/th") == "kasikornbank.com"
    assert normalise("line_id", "@CondoAdmin") == "condoadmin"


BASE = {"summary": "x", "red_flags": [], "recommended_actions": []}


def test_legit_cannot_be_high_risk():
    with pytest.raises(ValidationError):
        Verdict.model_validate({**BASE, "scam_type": "legit", "risk_level": "high"})


def test_scam_type_cannot_be_low_risk():
    with pytest.raises(ValidationError):
        Verdict.model_validate({**BASE, "scam_type": "fake_parcel", "risk_level": "low"})


def test_flagged_risk_needs_a_red_flag():
    with pytest.raises(ValidationError):
        Verdict.model_validate({**BASE, "scam_type": "other", "risk_level": "medium"})


def test_string_lists_are_wrapped():
    v = Verdict.model_validate({**BASE, "scam_type": "legit", "risk_level": "low",
                                "recommended_actions": ["ลบข้อความ"]})
    assert v.recommended_actions[0].text == "ลบข้อความ"


def test_extract_json_from_fenced_reply():
    assert extract_json('Sure:\n```json\n{"a": 1}\n```') == {"a": 1}


def test_ungrounded_quote_dropped():
    v = Verdict.model_validate({**BASE, "scam_type": "job_task", "risk_level": "high",
                                "red_flags": [{"text": "a", "quote": "รายได้วันละ"},
                                              {"text": "b", "quote": "not in message"}]})
    v = ground_quotes(v, "รายได้วันละ 3,000 บาท")
    assert v.red_flags[0].quote == "รายได้วันละ"
    assert v.red_flags[1].quote is None
