import { CheckCircle, Question, Warning, WarningOctagon } from "@phosphor-icons/react/dist/ssr";
import type { Icon } from "@phosphor-icons/react";
import { riskView, type RiskView } from "@/lib/display";
import type { Dict } from "@/lib/i18n";
import type { Verdict } from "@/lib/types";

/** Risk is always shown as icon + words, never colour alone. */
export const RISK_ICON: Record<RiskView, Icon> = {
  high: WarningOctagon, medium: Warning, low: CheckCircle, genuine: CheckCircle, insufficient: Question,
};

/** Text for the share dialog / clipboard: `body` is the chat bubble, `full` adds the headline and summary. */
export function shareTexts(v: Verdict, t: Dict) {
  const [label, sub] = t.risk[riskView(v)];
  const todo = v.recommended_actions.slice(0, 3).map((a) => `• ${a.text}${a.phone ? " " + a.phone : ""}`).join("\n");
  const body = `${t.share_lead}\n${t.share_type}: ${t.scam_type[v.scam_type]}\n${t.share_todo}:\n${todo}`;
  return { body, full: `${label} — ${sub}\n${v.summary}\n\n${body}` };
}
