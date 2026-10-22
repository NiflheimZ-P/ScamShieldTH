"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { RateLimitError, scan } from "@/lib/scan-client";
import type { Channel, Tone, ToolName, Verdict } from "@/lib/types";

export type Screen = "check" | "analysing" | "verdict";
export type Phase = "running" | "stopped" | "error";

export interface StepState {
  id: string;
  tool: ToolName;
  args: Record<string, string>;
  status: "running" | "done" | "stopped";
  summary?: string;
  tone?: Tone;
}

export interface ScanState {
  screen: Screen;
  phase: Phase;
  steps: StepState[];
  summarizing: boolean;
  verdict: Verdict | null;
  elapsedMs: number;
  rateLeft: number;
  /** Message + channel the current run was started with (shown beside the timeline / verdict). */
  submitted: { message: string; channel: Channel | null } | null;
}

const INITIAL: ScanState = {
  screen: "check", phase: "running", steps: [], summarizing: false, verdict: null, elapsedMs: 0, rateLeft: 0, submitted: null,
};

export function useScan() {
  const [state, setState] = useState<ScanState>(INITIAL);
  const abortRef = useRef<AbortController | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const rateRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopTimer = () => {
    if (tickRef.current) clearInterval(tickRef.current);
    tickRef.current = null;
  };

  const startRateCountdown = useCallback((seconds: number) => {
    if (rateRef.current) clearInterval(rateRef.current);
    setState((s) => ({ ...s, rateLeft: seconds }));
    rateRef.current = setInterval(() => {
      setState((s) => {
        if (s.rateLeft <= 1) {
          if (rateRef.current) clearInterval(rateRef.current);
          return { ...s, rateLeft: 0 };
        }
        return { ...s, rateLeft: s.rateLeft - 1 };
      });
    }, 1000);
  }, []);

  const run = useCallback(
    async (message: string, channel: Channel | null) => {
      abortRef.current?.abort();
      stopTimer();
      const controller = new AbortController();
      abortRef.current = controller;
      const t0 = Date.now();
      setState((s) => ({ ...INITIAL, rateLeft: s.rateLeft, screen: "analysing", submitted: { message, channel } }));
      tickRef.current = setInterval(() => setState((s) => ({ ...s, elapsedMs: Date.now() - t0 })), 200);

      try {
        for await (const ev of scan({ message, channel }, controller.signal)) {
          switch (ev.type) {
            case "step":
              setState((s) => ({ ...s, steps: [...s.steps, { id: ev.id, tool: ev.tool, args: ev.args, status: "running" }] }));
              break;
            case "observation":
              setState((s) => ({
                ...s,
                steps: s.steps.map((x) => (x.id === ev.id ? { ...x, status: "done", summary: ev.summary, tone: ev.tone } : x)),
              }));
              break;
            case "summarizing":
              setState((s) => ({ ...s, summarizing: true }));
              break;
            case "verdict":
              stopTimer();
              setState((s) => ({ ...s, screen: "verdict", verdict: ev.verdict, summarizing: false }));
              return;
            case "error":
              throw new Error(ev.message);
          }
        }
        throw new Error("stream ended without a verdict");
      } catch (err) {
        stopTimer();
        if (controller.signal.aborted) return; // stop() already updated the state
        if (err instanceof RateLimitError) {
          setState((s) => ({ ...s, screen: "check" }));
          startRateCountdown(err.retryAfter);
          return;
        }
        console.error("scan failed", err);
        setState((s) => ({ ...s, phase: "error", summarizing: false }));
      }
    },
    [startRateCountdown],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    stopTimer();
    setState((s) => ({
      ...s,
      phase: "stopped",
      summarizing: false,
      steps: s.steps.map((x) => (x.status === "running" ? { ...x, status: "stopped" } : x)),
    }));
  }, []);

  const retry = useCallback(() => {
    if (state.submitted) void run(state.submitted.message, state.submitted.channel);
  }, [run, state.submitted]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    stopTimer();
    setState((s) => ({ ...INITIAL, rateLeft: s.rateLeft }));
  }, []);

  useEffect(
    () => () => {
      abortRef.current?.abort();
      stopTimer();
      if (rateRef.current) clearInterval(rateRef.current);
    },
    [],
  );

  return { state, run, stop, retry, reset };
}
