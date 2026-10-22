// Pure mapping from API data to what the UI shows. No React here, so it stays easy to test.

import type { RedFlag, ToolName, Verdict } from "./types";

export type RiskView = "high" | "medium" | "low" | "genuine" | "insufficient";
export type RiskAttr = "high" | "medium" | "low" | "info";
export type ToolView = "search" | "url" | "phone" | "line" | "account" | "inspect";

export function riskView(v: Verdict): RiskView {
  if (v.risk_level === "unknown") return "insufficient";
  if (v.scam_type === "legit" && v.risk_level === "low") return "genuine";
  return v.risk_level;
}

export const RISK_ATTR: Record<RiskView, RiskAttr> = {
  high: "high", medium: "medium", low: "low", genuine: "low", insufficient: "info",
};

/** Position on the 3-step meter (0 = no meter). */
export const RISK_METER: Record<RiskView, number> = {
  high: 3, medium: 2, low: 1, genuine: 1, insufficient: 0,
};

export function toolView(tool: ToolName, args: Record<string, string>): ToolView {
  if (tool === "search_advisories") return "search";
  if (tool === "inspect_url") return "inspect";
  switch (args.kind) {
    case "phone": return "phone";
    case "line_id": return "line";
    case "bank_account": return "account";
    default: return "url";
  }
}

/** The one argument worth showing as a chip. */
export function toolArg(args: Record<string, string>): string {
  return args.query ?? args.value ?? args.url ?? Object.values(args)[0] ?? "";
}

export interface Segment {
  text: string;
  /** 1-based red-flag number, when this span is a flagged quote. */
  flag?: number;
}

/** Split the message so each flag's quote (first occurrence, non-overlapping) becomes a marked span. */
export function highlight(message: string, flags: RedFlag[]): Segment[] {
  const spans: { start: number; end: number; flag: number }[] = [];
  flags.forEach((f, i) => {
    if (!f.quote) return;
    const start = message.indexOf(f.quote);
    if (start === -1) return; // quote not in the message: list the flag, don't mark anything
    const end = start + f.quote.length;
    if (spans.some((s) => start < s.end && end > s.start)) return;
    spans.push({ start, end, flag: i + 1 });
  });
  spans.sort((a, b) => a.start - b.start);

  const out: Segment[] = [];
  let pos = 0;
  for (const s of spans) {
    if (s.start > pos) out.push({ text: message.slice(pos, s.start) });
    out.push({ text: message.slice(s.start, s.end), flag: s.flag });
    pos = s.end;
  }
  if (pos < message.length) out.push({ text: message.slice(pos) });
  return out;
}

export function hostOf(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
}
