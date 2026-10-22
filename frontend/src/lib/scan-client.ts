// POST /api/scan and read the SSE stream with a buffered fetch reader (L4).

import { mockScan } from "./mock-scan";
import type { ScanEvent, ScanRequest } from "./types";

export class RateLimitError extends Error {
  constructor(public retryAfter: number) {
    super("rate limited");
  }
}

export class ScanHttpError extends Error {
  constructor(public status: number, detail: string) {
    super(detail);
  }
}

const USE_MOCK = process.env.NEXT_PUBLIC_SCAN_MOCK === "1";

export async function* scan(req: ScanRequest, signal: AbortSignal): AsyncGenerator<ScanEvent> {
  if (USE_MOCK) {
    yield* mockScan(req, signal);
    return;
  }

  const res = await fetch("/api/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
  if (res.status === 429) {
    throw new RateLimitError(Number(res.headers.get("Retry-After")) || 30);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : `HTTP ${res.status}`;
    throw new ScanHttpError(res.status, detail);
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? ""; // keep the trailing partial frame for the next read
    for (const frame of frames) {
      if (!frame.startsWith("data: ")) continue; // comments / heartbeats
      const payload = frame.slice(6);
      if (payload === "[DONE]") return;
      yield JSON.parse(payload) as ScanEvent;
    }
  }
}
