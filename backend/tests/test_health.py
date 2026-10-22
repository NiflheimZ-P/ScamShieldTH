import base64

import httpx

from app.main import app


async def test_health():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_extract_text_rejects_non_image():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
        fake_png = "data:image/png;base64," + base64.b64encode(b"<script>alert(1)</script>" * 4).decode()
        r = await ac.post("/api/extract-text", json={"image": fake_png})
        r2 = await ac.post("/api/extract-text", json={"image": "data:text/html;base64,PGh0bWw+" + "A" * 40})
    assert r.status_code == 422  # magic bytes don't match PNG
    assert r2.status_code == 422  # not an allowed image type


async def test_scan_rejects_empty_message():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/api/scan", json={"message": ""})
    assert r.status_code == 422
