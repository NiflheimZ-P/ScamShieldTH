"use client";

import {
  ArrowClockwise, CircleNotch, DotsThree, Hand, Pause, Plugs, Sparkle, Stop, Timer, Warning,
} from "@phosphor-icons/react/dist/ssr";
import type { ScanState } from "@/hooks/useScan";
import { StepItem } from "./StepItem";
import { useUi } from "./Providers";

interface Props {
  state: ScanState;
  onStop: () => void;
  onRetry: () => void;
  onEdit: () => void;
}

export function AnalysingScreen({ state, onStop, onRetry, onEdit }: Props) {
  const { t } = useUi();
  const { phase, steps, summarizing, submitted } = state;
  const running = phase === "running";
  const anyStepRunning = steps.some((s) => s.status === "running");
  const sec = Math.floor(state.elapsedMs / 1000);

  const title = phase === "error" ? t.err_an_h : phase === "stopped" ? t.stopped_h : t.an_h;
  const sub = phase === "error" ? t.err_an_sub : phase === "stopped" ? t.stopped_sub : t.an_sub;
  const HeadIcon = phase === "error" ? Warning : phase === "stopped" ? Pause : CircleNotch;

  return (
    <main className="ss-main" style={{ paddingTop: 44, animation: "ss-in .3s ease-out" }}>
      <section className="ss-an-col" aria-labelledby="ss-an-h">
        <div className="ss-an-head">
          <span className="ss-an-badge">
            <HeadIcon aria-hidden className={running ? "ss-spin" : undefined} />
          </span>
          <div style={{ flex: 1, minWidth: 240 }}>
            <h1 id="ss-an-h" className="ss-an-title">{title}</h1>
            <p className="ss-muted" style={{ margin: 0, fontSize: 17 }}>{sub}</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="ss-muted" style={{ fontVariantNumeric: "tabular-nums", fontSize: 16 }} aria-label={t.elapsed}>
              <Timer aria-hidden style={{ verticalAlign: "-2px" }} /> {Math.floor(sec / 60)}:{String(sec % 60).padStart(2, "0")}
            </span>
            {running && (
              <button className="btn btn-secondary" onClick={onStop} style={{ minHeight: 46, padding: "0 18px", fontSize: 17 }}>
                <Stop aria-hidden weight="fill" />
                {t.stop}
              </button>
            )}
          </div>
        </div>

        <ol aria-live="polite" aria-relevant="additions text" className="ss-timeline">
          {steps.map((s, i) => (
            <StepItem key={s.id} step={s} index={i} />
          ))}
          {running && summarizing && (
            <li className="ss-step">
              <span className="ss-step-dot" data-pending="summary"><Sparkle aria-hidden className="ss-pulse" /></span>
              <div style={{ padding: "8px 0" }}><span className="ss-step-label">{t.summarizing}</span></div>
            </li>
          )}
          {running && !summarizing && !anyStepRunning && (
            <li className="ss-step">
              <span className="ss-step-dot" data-pending="plan"><DotsThree aria-hidden size={22} className="ss-pulse" /></span>
              <div className="ss-muted" style={{ padding: "9px 0" }}>{t.planning}</div>
            </li>
          )}
        </ol>

        {phase === "error" && (
          <div role="alert" data-risk="medium" className="ss-alert">
            <Plugs aria-hidden size={28} style={{ color: "var(--r-fg)" }} />
            <div style={{ flex: 1, minWidth: 240 }}>
              <div style={{ fontSize: 19, fontWeight: 500, marginBottom: 4 }}>{t.error_h}</div>
              <div style={{ fontSize: 16 }}>{t.error_sub}</div>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button className="btn btn-primary" onClick={onRetry} style={{ minHeight: 46, padding: "0 20px", fontSize: 17 }}>
                <ArrowClockwise aria-hidden />
                {t.retry}
              </button>
              <button className="btn btn-secondary" onClick={onEdit} style={{ minHeight: 46, padding: "0 18px", fontSize: 17 }}>
                {t.edit}
              </button>
            </div>
          </div>
        )}
        {phase === "stopped" && (
          <div style={{ marginTop: 8, display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button className="btn btn-primary ss-btn-lg" onClick={onRetry}>
              <ArrowClockwise aria-hidden />
              {t.resume}
            </button>
            <button className="btn btn-secondary ss-btn-lg" onClick={onEdit}>{t.edit}</button>
          </div>
        )}
      </section>

      <aside className="ss-panel ss-msg-aside">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontWeight: 500 }}>{t.your_msg}</span>
          <span className="tag ss-tag-soft">{submitted?.channel ? t.ch[submitted.channel] : t.ch_none}</span>
        </div>
        <div className="ss-msg-text">{submitted?.message}</div>
        <div className="ss-wait-tip">
          <Hand aria-hidden size={19} style={{ marginTop: 2, flex: "none" }} />
          <span>{t.wait_tip}</span>
        </div>
      </aside>
    </main>
  );
}
