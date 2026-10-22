"use client";

import { CircleNotch, ImageSquare, WarningCircle, X } from "@phosphor-icons/react/dist/ssr";
import { useCallback, useEffect, useRef, useState } from "react";
import { ExtractError, extractText, imageFrom, isImage, prepareImage } from "@/lib/extract-client";
import { useUi } from "./Providers";

interface Props {
  /** An image pasted onto the page before the dialog opened. */
  initial: File | null;
  onClose: () => void;
  onDone: (text: string, previewUrl: string) => void;
}

type State = { kind: "idle" } | { kind: "reading"; preview: string } | { kind: "error"; message: string; preview?: string };

export function ImageDialog({ initial, onClose, onDone }: Props) {
  const { t } = useUi();
  const [state, setState] = useState<State>({ kind: "idle" });
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const read = useCallback(async (file: File) => {
    if (!isImage(file)) {
      setState({ kind: "error", message: t.img_err_type });
      return;
    }
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    let preview = "";
    try {
      preview = await prepareImage(file);
      setState({ kind: "reading", preview });
      const text = await extractText(preview, ctrl.signal);
      if (!text.trim()) {
        setState({ kind: "error", message: t.img_err_empty, preview });
        return;
      }
      onDone(text, preview);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const message = e instanceof ExtractError ? e.message : t.img_err_generic;
      setState({ kind: "error", message, preview: preview || undefined });
    }
  }, [onDone, t]);

  const startedRef = useRef(false);
  useEffect(() => {
    if (initial && !startedRef.current) {
      startedRef.current = true; // read the pasted image once, not on every re-render
      void read(initial);
    }
  }, [initial, read]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    const onPaste = (e: ClipboardEvent) => {
      const f = imageFrom(e.clipboardData);
      if (f) {
        e.preventDefault();
        void read(f);
      }
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("paste", onPaste);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("paste", onPaste);
      abortRef.current?.abort();
    };
  }, [onClose, read]);

  const busy = state.kind === "reading";
  const preview = state.kind === "idle" ? undefined : state.preview;

  return (
    <div className="ss-backdrop" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="ss-img-h" className="ss-dialog" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <h2 id="ss-img-h" style={{ fontSize: 22, lineHeight: 1.4, margin: 0 }}>{t.img_h}</h2>
            <p className="ss-muted" style={{ margin: 0, fontSize: 15 }}>{t.img_sub}</p>
          </div>
          <button className="btn btn-secondary" onClick={onClose} aria-label={t.close} style={{ width: 40, height: 40, padding: 0 }}>
            <X aria-hidden />
          </button>
        </div>

        <button
          type="button"
          className="ss-drop"
          data-drag={drag}
          disabled={busy}
          autoFocus
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            const f = imageFrom(e.dataTransfer);
            if (f) void read(f);
            else setState({ kind: "error", message: t.img_err_type });
          }}
        >
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element -- local data URL preview
            <img src={preview} alt="" className="ss-drop-preview" />
          ) : (
            <ImageSquare aria-hidden size={40} className="ss-accent-icon" />
          )}
          {busy ? (
            <span className="ss-drop-main" role="status">
              <CircleNotch aria-hidden size={20} className="ss-spin" /> {t.img_reading}
            </span>
          ) : (
            <>
              <span className="ss-drop-main">{preview ? t.img_choose_other : t.img_choose}</span>
              <span className="ss-muted" style={{ fontSize: 15 }}>{t.img_paste_hint}</span>
            </>
          )}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = ""; // allow picking the same file again
            if (f) void read(f);
          }}
        />

        {state.kind === "error" && (
          <div role="alert" className="ss-error">
            <WarningCircle aria-hidden weight="fill" size={22} style={{ marginTop: 2, flex: "none" }} />
            <span>{state.message}</span>
          </div>
        )}
        <p className="ss-muted" style={{ margin: 0, fontSize: 14 }}>{t.img_privacy}</p>
      </div>
    </div>
  );
}
