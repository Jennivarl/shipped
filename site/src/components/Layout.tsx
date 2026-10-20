import type { ReactNode } from "react";
import { GOAL, POT, REPO, WATCH, addressUrl, short } from "../lib/chain";
import { Account } from "./Account";

/**
 * A package seen from above, its lid checked off: a release that exists and
 * was verified. Three faces in three greens so it reads as a box even small.
 */
export function Mark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 2.5 29 9.6 16 16.7 3 9.6Z" fill="#3ddc84" />
      <path d="M3 9.6 16 16.7V30L3 22.9Z" fill="#1f8f52" />
      <path d="M29 9.6V22.9L16 30V16.7Z" fill="#2cbf6f" />
      <path d="M10.6 9.4l3.6 2.1 7.2-4.2" fill="none" stroke="#04130a" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Logo() {
  return (
    <a href="#/" className="flex items-center gap-2.5 no-underline">
      <Mark />
      <span className="text-[21px] font-bold tracking-tight text-ink">
        shipped<span className="text-accent">.</span>
      </span>
    </a>
  );
}

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-page/85 backdrop-blur">
      <div className="mx-auto flex h-[68px] max-w-[1180px] items-center justify-between px-5">
        <div className="flex items-center gap-10">
          <Logo />
          <nav className="mono hidden items-center gap-7 text-[13.5px] text-body md:flex">
            <a href="#/#how" className="no-underline hover:text-accent">how it works</a>
            <a href="#/#goals" className="no-underline hover:text-accent">releases</a>
            <a href={REPO} target="_blank" rel="noreferrer" className="no-underline hover:text-accent">source</a>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <Account />
          <a href="#/start" className="btn btn-primary hidden no-underline sm:inline-flex">Start a goal</a>
        </div>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-28 border-t border-line">
      <div className="mx-auto grid max-w-[1180px] gap-10 px-5 py-14 md:grid-cols-[1.2fr_1fr]">
        <div>
          <Logo />
          <p className="mt-4 max-w-[420px] text-[14.5px] leading-relaxed text-body">
            Release bounties settled by GenLayer consensus reading the public registry. The maintainer is paid only when
            the release exists, names them, and was seen before the deadline.
          </p>
        </div>
        <div className="mono grid gap-2 text-[12.5px] text-body">
          <span className="text-ink">// live on GenLayer Studio Next</span>
          {[
            ["GOAL ", GOAL],
            ["WATCH", WATCH],
            ["POT  ", POT],
          ].map(([k, a]) => (
            <a key={k} href={addressUrl(a)} target="_blank" rel="noreferrer" className="whitespace-pre no-underline hover:text-accent">
              {k}  {short(a, 10, 6)}
            </a>
          ))}
          <a href={REPO} target="_blank" rel="noreferrer" className="mt-2 text-accent no-underline">
            → source and tests on GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}

export function Page({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <Header />
      {children}
      <Footer />
    </div>
  );
}
