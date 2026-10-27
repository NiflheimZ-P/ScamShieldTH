from starlette.requests import Request

from app.api.rate_limit import SlidingWindow, client_key


def test_sliding_window_blocks_then_recovers():
    w = SlidingWindow(limit=2, seconds=60)
    assert w.check("a", 0) == 0
    assert w.check("a", 1) == 0
    assert w.check("a", 2) == 58  # third hit waits until the first leaves the window
    assert w.check("b", 2) == 0  # other clients are unaffected
    assert w.check("a", 60) == 0


def test_client_key_uses_first_forwarded_hop():
    req = Request({"type": "http", "headers": [(b"x-forwarded-for", b"203.0.113.7, 10.0.0.1")], "client": ("10.0.0.1", 1)})
    assert client_key(req) == "203.0.113.7"
    assert client_key(Request({"type": "http", "headers": [], "client": ("10.0.0.2", 1)})) == "10.0.0.2"
