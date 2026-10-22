"use client";

import { Moon, ShieldCheck, Sun } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUi } from "./Providers";

/** Header + footer around a page. `onHome` lets the check page reset itself when its own nav link is clicked. */
export function AppShell({ children, onHome }: { children: React.ReactNode; onHome?: () => void }) {
  const { t, lang, setLang, theme, toggleTheme } = useUi();
  const path = usePathname();
  const onCheckPage = path === "/";

  return (
    <div className="ss-app">
      <header className="ss-header">
        <div className="ss-header-inner">
          <Link href="/" onClick={onHome} aria-label="ScamShield TH" className="ss-brand">
            <span className="ss-brand-mark"><ShieldCheck aria-hidden /></span>
            <span className="ss-brand-name">ScamShield</span>
            <span className="tag tag-outline ss-brand-tag">TH</span>
          </Link>
          <nav className="ss-nav">
            <Link href="/" onClick={onHome} className="ss-nav-link" aria-current={onCheckPage ? "page" : undefined}>
              {t.nav_check}
            </Link>
            <Link href="/about" className="ss-nav-link" aria-current={path === "/about" ? "page" : undefined}>
              {t.nav_about}
            </Link>
          </nav>
          <div className="seg" role="radiogroup" aria-label="Language">
            <label className="seg-opt ss-seg-opt">
              <input type="radio" name="ss-lang" checked={lang === "th"} onChange={() => setLang("th")} />
              ไทย
            </label>
            <label className="seg-opt ss-seg-opt">
              <input type="radio" name="ss-lang" checked={lang === "en"} onChange={() => setLang("en")} />
              EN
            </label>
          </div>
          <button className="btn btn-secondary ss-btn-icon" onClick={toggleTheme} aria-label={t.theme_label}>
            {theme === "light" ? <Moon aria-hidden /> : <Sun aria-hidden />}
          </button>
        </div>
      </header>

      {children}

      <footer className="ss-footer">
        <div className="ss-footer-inner">
          <span>{t.footer}</span>
          <span>{t.footer_r}</span>
        </div>
      </footer>
    </div>
  );
}
