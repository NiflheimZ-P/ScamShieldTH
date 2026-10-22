"use client";

import {
  ArrowCounterClockwise, ArrowSquareOut, Books, CaretDown, CaretUp, ChatText, Copy, ListChecks, Path, Phone, ShareFat,
} from "@phosphor-icons/react/dist/ssr";
import { useEffect, useRef, useState } from "react";
import { highlight, hostOf, RISK_ATTR, RISK_METER, riskView } from "@/lib/display";
import type { StepState } from "@/hooks/useScan";
import type { Channel, Verdict } from "@/lib/types";
import { RISK_ICON, shareTexts } from "./risk";
import { ShareDialog } from "./ShareDialog";
import { StepItem } from "./StepItem";
import { useUi } from "./Providers";

export type VerdictLayout = "a" | "b" | "c";

interface Props {
  verdict: Verdict;
  message: string;
  channel: Channel | null;
  steps: StepState[];
  layout?: VerdictLayout;
  onAgain: () => void;
  onToast: (msg: string) => void;
}

export function VerdictScreen({ verdict: v, message, channel, steps, layout = "a", onAgain, onToast }: Props) {
  const { t } = useUi();
  const [howOpen, setHowOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);

  // Analysing → Verdict: move focus to the risk heading so screen readers announce the result.
  useEffect(() => headingRef.current?.focus(), []);

  const view = riskView(v);
  const RiskIcon = RISK_ICON[view];
  const [label, sub] = t.risk[view];
  const meterAt = RISK_METER[view];
  const typeLabel = t.scam_type[v.scam_type];
  const segments = highlight(message, v.red_flags);

  const copy = () => {
    navigator.clipboard?.writeText(shareTexts(v, t).full).catch(() => {});
    onToast(t.copied);
  };

  return (
    <main className="ss-verdict-main">
      <div className="ss-verdict-grid" data-layout={layout} data-risk={RISK_ATTR[view]}>
        <section aria-labelledby="ss-risk" className="ss-banner">
          <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>
            <span className="ss-banner-icon"><RiskIcon aria-hidden weight="fill" /></span>
            <div style={{ flex: "1 1 300px", minWidth: 0 }}>
              <div className="ss-kicker">{t.risk_level}</div>
              <h1 id="ss-risk" ref={headingRef} tabIndex={-1} className="ss-risk-h">
                {label} <span className="ss-risk-sub">— {sub}</span>
              </h1>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                <span className="tag ss-risk-tag">{t.type}: {typeLabel}</span>
                <span className="tag ss-risk-tag">{channel ? t.ch[channel] : t.ch_none}</span>
              </div>
              <p className="ss-summary">{v.summary}</p>
            </div>
          </div>

          {meterAt > 0 && (
            <div role="img" aria-label={`${t.risk_level}: ${label}`} className="ss-meter">
              {t.meter.map((m, i) => (
                <div key={m} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <span className="ss-meter-bar" data-on={meterAt >= i + 1} />
                  <span className="ss-meter-label" data-current={meterAt === i + 1}>{m}</span>
                </div>
              ))}
            </div>
          )}

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button className="btn btn-primary ss-btn-lg ss-btn-risk-primary" onClick={() => setShareOpen(true)}>
              <ShareFat aria-hidden />
              {t.share}
            </button>
            <button className="btn btn-secondary ss-btn-lg ss-btn-risk" onClick={copy}>
              <Copy aria-hidden />
              {t.copy}
            </button>
            <button className="btn btn-secondary ss-btn-lg ss-btn-risk" onClick={onAgain}>
              <ArrowCounterClockwise aria-hidden />
              {t.again}
            </button>
          </div>
        </section>

        <section aria-labelledby="ss-acts" className="ss-panel" style={{ gridArea: "acts" }}>
          <h2 id="ss-acts" className="ss-h2"><ListChecks aria-hidden />{t.acts_h}</h2>
          <ol className="ss-actions">
            {v.recommended_actions.map((a, i) => (
              <li key={i} className="ss-action">
                <span className="ss-num">{i + 1}</span>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: 18, lineHeight: 1.6 }}>{a.text}</div>
                  {a.note && <div className="ss-muted" style={{ fontSize: 15, marginTop: 2 }}>{a.note}</div>}
                  {a.phone && (
                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 10, flexWrap: "wrap" }}>
                      <span className="ss-phone">{a.phone}</span>
                      <a className="btn btn-primary" href={`tel:${a.phone}`} style={{ minHeight: 44, padding: "0 16px", fontSize: 16, textDecoration: "none" }}>
                        <Phone aria-hidden />
                        {t.call}
                      </a>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="ss-msg-h" className="ss-panel" style={{ gridArea: "msg" }}>
          <h2 id="ss-msg-h" className="ss-h2" style={{ marginBottom: 14 }}><ChatText aria-hidden />{t.msg_h}</h2>
          <div className="ss-evidence">
            {segments.map((g, i) =>
              g.flag ? (
                <mark key={i} className="ss-mark">{g.text}<sup>{g.flag}</sup></mark>
              ) : (
                <span key={i}>{g.text}</span>
              ),
            )}
          </div>
          <h3 style={{ fontSize: 19, lineHeight: 1.4, margin: "22px 0 10px" }}>
            {t.flags_h} <span className="ss-muted" style={{ fontWeight: 400 }}>({v.red_flags.length})</span>
          </h3>
          {v.red_flags.length > 0 ? (
            <ul className="ss-flags">
              {v.red_flags.map((f, i) => (
                <li key={i} className="ss-flag">
                  <span className="ss-flag-n">{i + 1}</span>
                  <span>{f.text}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="ss-muted" style={{ margin: 0, fontSize: 16 }}>{t.no_flags}</p>
          )}
        </section>

        <section aria-labelledby="ss-src" style={{ gridArea: "src", minWidth: 0, padding: "4px 2px" }}>
          <h2 id="ss-src" className="ss-h2" style={{ fontSize: 21, marginBottom: 4 }}><Books aria-hidden />{t.src_h}</h2>
          <p className="ss-muted" style={{ margin: "0 0 12px", fontSize: 14 }}>{t.src_note}</p>
          {v.citations.length > 0 ? (
            <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {v.citations.map((c, i) => (
                <li key={i}>
                  <a href={c.url} target="_blank" rel="noopener noreferrer" className="ss-cite">
                    <span className="ss-mono ss-muted" style={{ fontSize: 13, paddingTop: 3 }}>[{i + 1}]</span>
                    <span style={{ minWidth: 0 }}>
                      <span style={{ display: "block", fontSize: 16, fontWeight: 500, lineHeight: 1.55 }}>{c.title}</span>
                      <span className="ss-muted" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 4, fontSize: 13 }}>
                        <span style={{ fontWeight: 500, color: "var(--color-text)" }}>{c.source}</span>
                        <span aria-hidden>·</span>
                        <span className="ss-mono">{hostOf(c.url)}</span>
                      </span>
                    </span>
                    <ArrowSquareOut aria-hidden className="ss-muted" style={{ paddingTop: 4 }} />
                  </a>
                </li>
              ))}
            </ol>
          ) : (
            <div className="ss-empty">{t.no_src}</div>
          )}
        </section>

        <section className="ss-how">
          <button className="ss-how-toggle" onClick={() => setHowOpen((o) => !o)} aria-expanded={howOpen} aria-controls="ss-how">
            <Path aria-hidden className="ss-accent-icon" />
            {t.how_h}
            <span className="ss-muted" style={{ fontSize: 15, fontWeight: 400 }}>{t.how_meta(steps.length)}</span>
            {howOpen ? <CaretUp aria-hidden style={{ marginLeft: "auto" }} /> : <CaretDown aria-hidden style={{ marginLeft: "auto" }} />}
          </button>
          {howOpen && (
            <ol id="ss-how" className="ss-how-list">
              {steps.map((s, i) => (
                <StepItem key={s.id} step={s} index={i} compact />
              ))}
            </ol>
          )}
          <p className="ss-muted" style={{ margin: "16px 0 0", fontSize: 14, maxWidth: "80ch" }}>{t.disclaimer}</p>
        </section>
      </div>

      {shareOpen && <ShareDialog verdict={v} onClose={() => setShareOpen(false)} onToast={onToast} />}
    </main>
  );
}
