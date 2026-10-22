"use client";

import { Copy, ShareFat, X } from "@phosphor-icons/react/dist/ssr";
import { useEffect } from "react";
import { RISK_ATTR, riskView } from "@/lib/display";
import type { Verdict } from "@/lib/types";
import { useUi } from "./Providers";
import { RISK_ICON, shareTexts } from "./risk";

export function ShareDialog({ verdict, onClose, onToast }: { verdict: Verdict; onClose: () => void; onToast: (m: string) => void }) {
  const { t } = useUi();
  const view = riskView(verdict);
  const RiskIcon = RISK_ICON[view];
  const [label, sub] = t.risk[view];
  const { body, full } = shareTexts(verdict, t);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const copy = () => {
    navigator.clipboard?.writeText(full).catch(() => {});
    onToast(t.copied);
  };
  const share = () => {
    if (navigator.share) navigator.share({ text: full }).catch(() => {});
    else copy();
  };

  return (
    <div className="ss-backdrop" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="ss-share-h" className="ss-dialog" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <h2 id="ss-share-h" style={{ fontSize: 22, lineHeight: 1.4, margin: 0 }}>{t.share_h}</h2>
            <p className="ss-muted" style={{ margin: 0, fontSize: 15 }}>{t.share_sub}</p>
          </div>
          <button className="btn btn-secondary" onClick={onClose} aria-label={t.close} style={{ width: 40, height: 40, padding: 0 }} autoFocus>
            <X aria-hidden />
          </button>
        </div>
        <div style={{ background: "var(--surface-2)", borderRadius: "var(--radius-md)", padding: "18px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="ss-muted" style={{ fontSize: 12, textAlign: "center" }}>{t.share_preview}</div>
          <div className="ss-bubble" data-risk={RISK_ATTR[view]}>
            <div className="ss-bubble-head"><RiskIcon aria-hidden weight="fill" />{label} — {sub}</div>
            <div style={{ padding: "10px 14px", fontSize: 15, lineHeight: 1.65, whiteSpace: "pre-line" }}>{body}</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button className="btn btn-primary ss-btn-lg" onClick={share} style={{ flex: 1 }}>
            <ShareFat aria-hidden />
            {t.share_send}
          </button>
          <button className="btn btn-secondary ss-btn-lg" onClick={copy} style={{ flex: 1 }}>
            <Copy aria-hidden />
            {t.share_copy}
          </button>
        </div>
      </div>
    </div>
  );
}
