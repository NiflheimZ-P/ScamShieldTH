# ScamShield TH — frontend

Next.js 15 (App Router) + TypeScript + Tailwind v4, Nocturne theme. Setup, architecture and evaluation are in the
[root README](../README.md).

- `src/lib/types.ts` mirrors the backend contract (`backend/app/api/schemas.py` + SSE events in `scan_service.py`).
- `/api/*` is rewritten to the FastAPI backend (`next.config.ts`, `BACKEND_URL`); the API key never reaches the browser.
- `NEXT_PUBLIC_SCAN_MOCK=1` replays the designer's sample scenarios without a backend (UI work only).
