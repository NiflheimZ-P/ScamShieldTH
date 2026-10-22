"""Offline tests for the link ↔ claimed-brand precheck."""

from app.agent.precheck import find_hosts, precheck
from app.config import get_settings
from app.repositories.brands import BrandRepository

BRANDS = BrandRepository(get_settings().brands_csv)


def test_find_hosts_handles_bare_domains_and_skips_email():
    msg = "ติดต่อ www.fir-line.cc หรือ fla-line.cc/x ไม่รับSMSแจ้งprivacy@bangchak.co.th https://bit.ly/abc"
    assert find_hosts(msg) == ["fir-line.cc", "fla-line.cc", "bit.ly"]


def test_consistent_brand_link():
    pc = precheck("แพ็กเกจ AIS PLAY เพิ่มเติม https://m.ais.co.th/abc", BRANDS)
    assert pc.consistent and any("CONSISTENT" in e for e in pc.evidence)


def test_mismatch_brand_link():
    pc = precheck("Bangkok Bank: แต้มใกล้หมดอายุแล้ว คลิกดู : https://kusor.cn/tns", BRANDS)
    assert not pc.consistent and any("MISMATCH" in e for e in pc.evidence)


def test_ascii_keyword_needs_word_boundary():
    assert BRANDS.mentioned_in("see details below") == []  # "ais" inside "details"


def test_no_link():
    pc = precheck("รหัส OTP ของคุณคือ 849201", BRANDS)
    assert pc.links == [] and pc.consistent
