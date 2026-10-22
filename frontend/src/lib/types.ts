// Mirrors backend/app/api/schemas.py and the SSE contract in backend/app/services/scan_service.py.

export type ScamType =
  | "fake_parcel"
  | "fake_bank_or_loan"
  | "investment"
  | "romance"
  | "job_task"
  | "phishing_link"
  | "gov_impersonation"
  | "prize_lottery"
  | "gambling"
  | "legit"
  | "other";

/** `unknown` = not enough information to judge. */
export type RiskLevel = "low" | "medium" | "high" | "unknown";

export type Channel = "sms" | "line" | "email" | "other";

export interface RedFlag {
  text: string;
  /** Exact substring of the user's message this flag points at (highlighted in the UI). */
  quote?: string | null;
}

export interface Action {
  text: string;
  note?: string | null;
  /** A hotline to show in large digits with a tel: button. */
  phone?: string | null;
}

export interface Citation {
  title: string;
  source: string;
  url: string;
}

export interface Verdict {
  scam_type: ScamType;
  risk_level: RiskLevel;
  summary: string;
  red_flags: RedFlag[];
  recommended_actions: Action[];
  citations: Citation[];
}

export type ToolName = "search_advisories" | "check_indicator" | "inspect_url";
export type Tone = "warn" | "ok" | "info";

export type ScanEvent =
  | { type: "step"; id: string; tool: ToolName; args: Record<string, string> }
  | { type: "observation"; id: string; tool: ToolName; summary: string; tone: Tone }
  | { type: "summarizing" }
  | { type: "verdict"; verdict: Verdict }
  | { type: "error"; message: string };

export interface ScanRequest {
  message: string;
  channel: Channel | null;
}
