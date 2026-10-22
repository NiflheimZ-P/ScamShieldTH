"use client";

import { ArrowRight, ChatText, ClipboardText, Robot, Wrench } from "@phosphor-icons/react/dist/ssr";
import { AppShell } from "@/components/AppShell";
import { useUi } from "@/components/Providers";

const PIPE_ICONS = [ChatText, Robot, Wrench, ClipboardText];

export default function About() {
  const { t } = useUi();
  return (
    <AppShell>
      <main className="ss-about ss-enter">
        <div>
          <h1 style={{ fontSize: 40, lineHeight: 1.35, margin: "0 0 12px" }}>{t.ab_h}</h1>
          <p className="ss-lead" style={{ maxWidth: "62ch" }}>{t.ab_lead}</p>
        </div>

        <section>
          <h2 style={{ fontSize: 24, lineHeight: 1.4, margin: "0 0 16px" }}>{t.ab_pipe}</h2>
          <div className="ss-pipe">
            {t.pipe.map(([title, body], i) => {
              const Icon = PIPE_ICONS[i];
              return (
                <div key={title} className="ss-pipe-step">
                  <div className="ss-pipe-card">
                    <Icon aria-hidden size={24} className="ss-accent-icon" />
                    <div style={{ fontWeight: 500, fontSize: 17 }}>{title}</div>
                    <div className="ss-muted" style={{ fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-line" }}>{body}</div>
                  </div>
                  {i < t.pipe.length - 1 && <ArrowRight aria-hidden size={20} className="ss-muted" />}
                </div>
              );
            })}
          </div>
        </section>

        <section>
          <h2 style={{ fontSize: 24, lineHeight: 1.4, margin: "0 0 12px" }}>{t.ab_data}</h2>
          <ul style={{ margin: 0, paddingLeft: 22, display: "flex", flexDirection: "column", gap: 6 }}>
            {t.ab_sources.map((s) => <li key={s}>{s}</li>)}
          </ul>
        </section>

        <section>
          <h2 style={{ fontSize: 24, lineHeight: 1.4, margin: "0 0 4px" }}>{t.ab_results}</h2>
          <p className="ss-muted" style={{ margin: "0 0 12px", fontSize: 15 }}>{t.ab_results_note}</p>
          <table className="table" style={{ fontSize: 16 }}>
            <thead>
              <tr>
                <th style={{ fontSize: 13 }}>{t.ab_metric}</th>
                <th style={{ fontSize: 13, textAlign: "right" }}>{t.ab_value}</th>
              </tr>
            </thead>
            <tbody>
              {t.ab_metrics.map((m) => (
                <tr key={m}>
                  <td style={{ padding: "12px 8px" }}>{m}</td>
                  <td className="ss-muted" style={{ padding: "12px 8px", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>—</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h2 style={{ fontSize: 24, lineHeight: 1.4, margin: "0 0 12px" }}>{t.ab_limits}</h2>
          <ul style={{ margin: 0, paddingLeft: 22, display: "flex", flexDirection: "column", gap: 6 }}>
            {t.ab_limit_items.map((s) => <li key={s}>{s}</li>)}
          </ul>
        </section>
      </main>
    </AppShell>
  );
}
