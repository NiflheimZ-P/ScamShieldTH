"use client";

import { Check } from "@phosphor-icons/react/dist/ssr";
import { useCallback, useEffect, useRef, useState } from "react";
import { AnalysingScreen } from "@/components/AnalysingScreen";
import { AppShell } from "@/components/AppShell";
import { CheckScreen } from "@/components/CheckScreen";
import { VerdictScreen, type VerdictLayout } from "@/components/VerdictScreen";
import { useScan } from "@/hooks/useScan";
import type { Channel } from "@/lib/types";

// Board option 1a (banner + two columns). "b" = side rail, "c" = actions first.
const VERDICT_LAYOUT: VerdictLayout = "a";

export default function Home() {
  const { state, run, stop, retry, reset } = useScan();
  const [text, setText] = useState("");
  const [channel, setChannel] = useState<Channel | null>(null);
  const [toast, setToast] = useState("");
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback((msg: string) => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(msg);
    toastTimer.current = setTimeout(() => setToast(""), 2400);
  }, []);
  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current); }, []);

  const again = () => {
    reset();
    setText("");
    setChannel(null);
  };

  return (
    <AppShell onHome={reset}>
      {state.screen === "check" && (
        <CheckScreen
          text={text}
          onText={setText}
          channel={channel}
          onChannel={setChannel}
          rateLeft={state.rateLeft}
          onSubmit={() => run(text, channel)}
        />
      )}
      {state.screen === "analysing" && <AnalysingScreen state={state} onStop={stop} onRetry={retry} onEdit={reset} />}
      {state.screen === "verdict" && state.verdict && state.submitted && (
        <VerdictScreen
          verdict={state.verdict}
          message={state.submitted.message}
          channel={state.submitted.channel}
          steps={state.steps}
          layout={VERDICT_LAYOUT}
          onAgain={again}
          onToast={showToast}
        />
      )}
      {toast && (
        <div role="status" className="ss-toast">
          <Check aria-hidden />
          {toast}
        </div>
      )}
    </AppShell>
  );
}
