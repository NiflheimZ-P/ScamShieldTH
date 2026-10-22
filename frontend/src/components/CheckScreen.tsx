"use client";

import {
  HourglassMedium, Image as ImageIcon, LockSimple, MagnifyingGlass, WarningCircle, X,
} from "@phosphor-icons/react/dist/ssr";
import { useCallback, useEffect, useState } from "react";
import { imageFrom } from "@/lib/extract-client";
import { EXAMPLE_KEYS, SCENARIOS } from "@/lib/mock-scan";
import type { Channel } from "@/lib/types";
import { ImageDialog } from "./ImageDialog";
import { useUi } from "./Providers";

export const MAX_CHARS = 4000;
const CHANNELS: Channel[] = ["sms", "line", "email", "other"];

interface Props {
  text: string;
  onText: (v: string) => void;
  channel: Channel | null;
  onChannel: (c: Channel) => void;
  rateLeft: number;
  onSubmit: () => void;
}

export function CheckScreen({ text, onText, channel, onChannel, rateLeft, onSubmit }: Props) {
  const { t, lang } = useUi();
  const [touched, setTouched] = useState(false);
  // Screenshot flow: dialog (button or pasted image) -> gemma reads the text -> textarea for review.
  const [dialog, setDialog] = useState<{ initial: File | null } | null>(null);
  const [thumb, setThumb] = useState<string | null>(null);

  const onImageText = useCallback((extracted: string, preview: string) => {
    onText(extracted);
    setThumb(preview);
    setTouched(false);
    setDialog(null);
  }, [onText]);
  const closeDialog = useCallback(() => setDialog(null), []);

  useEffect(() => {
    if (dialog) return; // the dialog handles paste while it is open
    const onPaste = (e: ClipboardEvent) => {
      const f = imageFrom(e.clipboardData);
      if (f) {
        e.preventDefault();
        setDialog({ initial: f });
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [dialog]);

  const over = text.length > MAX_CHARS;
  const empty = !text.trim();
  const errText = over ? t.err_long : touched && empty ? t.err_empty : "";
  const disabled = empty || over || rateLeft > 0;

  const submit = () => {
    setTouched(true);
    if (!disabled) onSubmit();
  };

  return (
    <main className="ss-main ss-enter">
      <div className="ss-check-col">
        <div>
          <h1 className="ss-h1">{t.h1}</h1>
          <p className="ss-lead">{t.lead}</p>
        </div>

        <div className="ss-panel ss-form">
          <div className="ss-form-head">
            <label htmlFor="ss-msg" className="ss-label">{t.label_msg}</label>
            <button className="btn btn-ghost" onClick={() => setDialog({ initial: null })} aria-haspopup="dialog" style={{ fontSize: 15, minHeight: 40, padding: "0 10px", color: "var(--accent-ink)" }}>
              <ImageIcon aria-hidden size={19} />
              {t.attach}
            </button>
          </div>

          {thumb && (
            <div className="ss-attach">
              {/* eslint-disable-next-line @next/next/no-img-element -- local data URL preview */}
              <img src={thumb} alt="" className="ss-attach-thumb ss-attach-img" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500 }}>{t.attach_done}</div>
                <div className="ss-muted" style={{ fontSize: 15 }}>{t.attach_note}</div>
              </div>
              <button className="btn btn-secondary ss-btn-icon" onClick={() => setThumb(null)} aria-label={t.remove} style={{ fontSize: 18 }}>
                <X aria-hidden />
              </button>
            </div>
          )}
          {dialog && <ImageDialog initial={dialog.initial} onClose={closeDialog} onDone={onImageText} />}

          <textarea
            id="ss-msg"
            className="input ss-textarea"
            value={text}
            onChange={(e) => onText(e.target.value)}
            onBlur={() => setTouched(true)}
            placeholder={t.placeholder}
            aria-invalid={!!errText}
            aria-describedby="ss-count ss-err"
          />

          <div className="ss-form-row">
            <span className="ss-muted" style={{ fontSize: 15 }}>{t.channel}</span>
            <div className="seg" role="radiogroup" aria-label={t.channel}>
              {CHANNELS.map((c) => (
                <label key={c} className="seg-opt" style={{ minHeight: 44, padding: "0 16px", fontSize: 15 }}>
                  <input type="radio" name="ss-ch" checked={channel === c} onChange={() => onChannel(c)} />
                  {t.ch[c]}
                </label>
              ))}
            </div>
            <span id="ss-count" className="ss-count" data-over={over}>
              {text.length.toLocaleString("en-US")} / {MAX_CHARS.toLocaleString("en-US")}
            </span>
          </div>

          {errText && (
            <div id="ss-err" role="alert" className="ss-error">
              <WarningCircle aria-hidden weight="fill" size={22} style={{ marginTop: 2, flex: "none" }} />
              <span>{errText}</span>
            </div>
          )}
          {rateLeft > 0 && (
            <div role="status" data-risk="medium" className="ss-notice">
              <HourglassMedium aria-hidden size={22} />
              <span>{t.rate(rateLeft)}</span>
            </div>
          )}

          <div className="ss-form-row">
            <button className="btn btn-primary ss-check-btn" disabled={disabled} onClick={submit}>
              <MagnifyingGlass aria-hidden size={21} />
              {rateLeft > 0 ? t.wait(rateLeft) : t.check}
            </button>
            <span className="ss-muted" style={{ fontSize: 15 }}>{t.check_hint}</span>
          </div>
        </div>
      </div>

      <aside className="ss-side-col">
        <div>
          <h2 style={{ fontSize: 21, lineHeight: 1.4, margin: "0 0 4px" }}>{t.examples}</h2>
          <p className="ss-muted" style={{ fontSize: 15, margin: 0 }}>{t.examples_sub}</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {EXAMPLE_KEYS.map((k) => {
            const ex = SCENARIOS[k];
            return (
              <button
                key={k}
                className="ss-example"
                onClick={() => {
                  onText(ex.message);
                  onChannel(ex.channel);
                  setTouched(false);
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="tag ss-tag-soft">{t.ch[ex.channel]}</span>
                  <span className="ss-example-title">{ex.title[lang]}</span>
                </span>
                <span className="ss-example-preview">{ex.message}</span>
              </button>
            );
          })}
        </div>
        <div className="ss-privacy">
          <LockSimple aria-hidden size={22} className="ss-accent-icon" style={{ marginTop: 2, flex: "none" }} />
          <div>
            <div style={{ fontWeight: 500, marginBottom: 2 }}>{t.privacy_t}</div>
            <div className="ss-muted" style={{ fontSize: 15 }}>{t.privacy}</div>
          </div>
        </div>
      </aside>
    </main>
  );
}
