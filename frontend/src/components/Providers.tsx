"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { DICTS, type Dict, type Lang } from "@/lib/i18n";

type Theme = "light" | "dark";

interface UiContext {
  lang: Lang;
  t: Dict;
  setLang: (l: Lang) => void;
  theme: Theme;
  toggleTheme: () => void;
}

const Ctx = createContext<UiContext | null>(null);

function stored<T extends string>(key: string, allowed: readonly T[]): T | null {
  try {
    const v = localStorage.getItem(key);
    return v && (allowed as readonly string[]).includes(v) ? (v as T) : null;
  } catch {
    return null;
  }
}

function save(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // private mode / blocked storage: the preference just isn't remembered
  }
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("th");
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    setLangState(stored("ss-lang", ["th", "en"] as const) ?? "th");
    setTheme(stored("ss-theme", ["light", "dark"] as const) ?? "light");
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.lang = lang;
  }, [theme, lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    save("ss-lang", l);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((cur) => {
      const next = cur === "light" ? "dark" : "light";
      save("ss-theme", next);
      return next;
    });
  }, []);

  const value = useMemo(() => ({ lang, t: DICTS[lang], setLang, theme, toggleTheme }), [lang, setLang, theme, toggleTheme]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useUi(): UiContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useUi must be used inside <Providers>");
  return ctx;
}
