"use client";

import {
  Bank, Browser, ChatCircle, CheckCircle, CircleNotch, DotsThree, Info, Link as LinkIcon, MagnifyingGlass, Pause, Phone, Warning,
} from "@phosphor-icons/react/dist/ssr";
import type { Icon } from "@phosphor-icons/react";
import { toolArg, toolView, type ToolView } from "@/lib/display";
import type { StepState } from "@/hooks/useScan";
import type { Tone } from "@/lib/types";
import { useUi } from "./Providers";

const TOOL_ICON: Record<ToolView, Icon> = {
  search: MagnifyingGlass, url: LinkIcon, phone: Phone, line: ChatCircle, account: Bank, inspect: Browser,
};

const TONE_ICON: Record<Tone, { icon: Icon; weight: "fill" | "regular" }> = {
  warn: { icon: Warning, weight: "fill" },
  ok: { icon: CheckCircle, weight: "fill" },
  info: { icon: Info, weight: "regular" },
};

/** One timeline row (analysing screen) or one card (`compact`, the verdict's "How did we decide?"). */
export function StepItem({ step, index, compact = false }: { step: StepState; index: number; compact?: boolean }) {
  const { t } = useUi();
  const view = toolView(step.tool, step.args);
  const ToolIcon = TOOL_ICON[view];
  const running = step.status === "running";
  const stopped = step.status === "stopped";

  const ResultIcon = running ? DotsThree : stopped ? Pause : TONE_ICON[step.tone ?? "info"].icon;
  const result = running ? t.running : stopped ? t.stopped_step : step.summary;
  const resultLine = (
    <div className={`ss-result${running ? " ss-pulse" : ""}`} data-tone={running || stopped ? undefined : step.tone}>
      <ResultIcon aria-hidden size={19} weight={running || stopped ? "regular" : TONE_ICON[step.tone ?? "info"].weight} />
      <span style={compact ? { fontSize: 15 } : undefined}>{result}</span>
    </div>
  );

  if (compact) {
    return (
      <li className="ss-how-item">
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 500 }}>
          <span className="ss-mono ss-muted" style={{ fontSize: 12 }}>{String(index + 1).padStart(2, "0")}</span>
          <ToolIcon aria-hidden className="ss-accent-icon" />
          {t.tools[view]}
        </div>
        <code className="ss-arg" style={{ fontSize: 13, alignSelf: "flex-start" }}>{toolArg(step.args)}</code>
        {resultLine}
      </li>
    );
  }

  return (
    <li className="ss-step">
      <div className="ss-step-rail">
        <span className="ss-step-dot">
          {running ? <CircleNotch aria-hidden className="ss-spin" /> : <ToolIcon aria-hidden />}
        </span>
        <span className="ss-step-line" />
      </div>
      <div className="ss-step-body">
        <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
          <span className="ss-step-label">{t.tools[view]}</span>
          <code className="ss-mono ss-muted" style={{ fontSize: 12 }}>{step.tool}</code>
        </div>
        <div style={{ margin: "6px 0 8px" }}>
          <span className="ss-arg">{toolArg(step.args)}</span>
        </div>
        {resultLine}
      </div>
    </li>
  );
}
