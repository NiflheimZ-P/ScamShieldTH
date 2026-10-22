// Screenshot -> text: shrink the image in the browser, then POST /api/extract-text (gemma vision).

export class ExtractError extends Error {}

const MAX_SIDE = 1600; // enough for phone screenshots; keeps the upload well under 1 MB

export function isImage(file: Blob): boolean {
  return /^image\/(png|jpeg|webp|gif|bmp)$/.test(file.type);
}

/** Re-encode as JPEG, longest side ≤ MAX_SIDE. Also strips metadata (location etc.). */
export async function prepareImage(file: Blob): Promise<string> {
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bmp.width * scale);
  canvas.height = Math.round(bmp.height * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new ExtractError("canvas unavailable");
  ctx.fillStyle = "#fff"; // transparent PNG -> white, not black
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bmp, 0, 0, canvas.width, canvas.height);
  bmp.close();
  return canvas.toDataURL("image/jpeg", 0.9);
}

export async function extractText(dataUrl: string, signal: AbortSignal): Promise<string> {
  const res = await fetch("/api/extract-text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: dataUrl }),
    signal,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ExtractError(typeof body?.detail === "string" ? body.detail : `HTTP ${res.status}`);
  }
  return typeof body?.text === "string" ? body.text : "";
}

/** First image in a paste/drop payload, if any. */
export function imageFrom(data: DataTransfer | null): File | null {
  if (!data) return null;
  for (const item of Array.from(data.items ?? [])) {
    if (item.kind === "file") {
      const f = item.getAsFile();
      if (f && isImage(f)) return f;
    }
  }
  return Array.from(data.files ?? []).find(isImage) ?? null;
}
