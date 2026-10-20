import { useState } from "react";
import { ConnectButton } from "../components/Account";
import { TxBanner } from "../components/Bits";
import { Page } from "../components/Layout";
import { useAccount, useTx } from "../lib/hooks";
import { postGoal } from "../lib/wallet";

/**
 * The same checks the contract makes, run first so a typo is caught before
 * anybody pays for a transaction the contract would refuse anyway.
 */
function problem(f: { name: string; registry: string; pkg: string; version: string; payee: string; days: string; unit: string }): string | null {
  if (!/^[a-z0-9_-]{1,40}$/.test(f.name)) return "A short name: lowercase letters, digits, - or _.";
  if (!f.pkg.trim()) return "Name the package.";
  if (f.registry === "npm" && f.pkg !== f.pkg.toLowerCase()) return "npm package names are lowercase.";
  if (!/^\d+(\.\d+){0,3}([-.]?[A-Za-z][A-Za-z0-9.-]*)?$/.test(f.version.trim())) return "The exact version, like 2.0.0 or 3.0.0-rc.1.";
  if (!/^0x[0-9a-fA-F]{40}$/.test(f.payee.trim())) return "The payee is a full 0x address.";
  const hours = Number(f.days) * (f.unit === "days" ? 24 : 1);
  if (!Number.isInteger(hours) || hours < 1 || hours > 366 * 24) return "A deadline an hour to 366 days away, in whole hours.";
  return null;
}

export default function Start() {
  const { account } = useAccount();
  const [f, setF] = useState({ name: "", registry: "pypi", pkg: "", version: "", payee: "", days: "30", unit: "days" });
  const [error, setError] = useState<string | null>(null);
  const { tx, busy, run, clear } = useTx();
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });
  const goalId = account ? `${account.toLowerCase()}:${f.name}` : "";

  return (
    <Page>
      <section className="mx-auto grid max-w-[1200px] gap-12 px-5 pt-14 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <h1 className="text-[52px] font-extrabold leading-[1.04] tracking-tight text-ink">Start a goal for a release.</h1>
          <p className="mt-5 max-w-[460px] text-[17px] leading-relaxed text-body">
            Name the package, the exact version you want, who should be paid, and the deadline. Once posted, none of it can
            change, so backers know exactly what they are funding.
          </p>
          <div className="card mt-8 p-6 text-[14.5px] leading-relaxed text-body">
            <div className="text-[16px] font-extrabold text-ink">If you are the maintainer</div>
            Put your payee address in the release's metadata before you publish: the README on PyPI, or{" "}
            <span className="mono">"funding": "0x…"</span> in package.json on npm. Then press <b>Check the registry</b> on the goal
            the moment it is live. The network has to see it before the deadline.
          </div>
        </div>

        <div className="card p-7">
          {!account ? (
            <>
              <div className="text-[20px] font-extrabold text-ink">Connect a wallet to post a goal</div>
              <p className="mt-2 text-[14.5px] text-body">Any browser wallet works. New wallets get test GEN automatically.</p>
              <div className="mt-6"><ConnectButton /></div>
            </>
          ) : (
            <form
              className="grid gap-4"
              onSubmit={(e) => {
                e.preventDefault();
                const why = problem(f);
                setError(why);
                if (why) return;
                run(`post the goal ${f.name}`, () =>
                  postGoal(f.name, f.registry, f.pkg.trim(), f.version.trim(), f.payee.trim(), Number(f.days) * (f.unit === "days" ? 24 : 1)),
                );
              }}
            >
              <div className="grid gap-4 sm:grid-cols-[1fr_140px]">
                <label className="grid gap-1.5 text-[13px] font-bold text-ink">
                  Package
                  <input className="field" placeholder="requests" value={f.pkg} onChange={set("pkg")} />
                </label>
                <label className="grid gap-1.5 text-[13px] font-bold text-ink">
                  Registry
                  <select className="field" value={f.registry} onChange={set("registry")}>
                    <option value="pypi">PyPI</option>
                    <option value="npm">npm</option>
                  </select>
                </label>
              </div>
              <label className="grid gap-1.5 text-[13px] font-bold text-ink">
                Exact version
                <input className="field" placeholder="2.33.0" value={f.version} onChange={set("version")} />
              </label>
              <label className="grid gap-1.5 text-[13px] font-bold text-ink">
                Paid to
                <input className="field mono" placeholder="0x…" value={f.payee} onChange={set("payee")} />
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="grid gap-1.5 text-[13px] font-bold text-ink">
                  Deadline in
                  <span className="flex gap-2">
                    <input className="field" value={f.days} onChange={set("days")} inputMode="numeric" />
                    <select className="field w-[110px]" value={f.unit} onChange={set("unit")}>
                      <option value="days">days</option>
                      <option value="hours">hours</option>
                    </select>
                  </span>
                </label>
                <label className="grid gap-1.5 text-[13px] font-bold text-ink">
                  Short name
                  <input className="field" placeholder="v2-release" value={f.name} onChange={set("name")} />
                </label>
              </div>
              <button type="submit" className="btn btn-primary mt-2" disabled={busy}>
                {busy ? "Posting…" : "Post the goal"}
              </button>
              {error && <p className="text-[13.5px] text-warn">{error}</p>}
              <TxBanner tx={tx} onClose={clear} />
              {tx?.state === "done" && (
                <a href={`#/goal?id=${encodeURIComponent(goalId)}`} className="btn btn-secondary no-underline">
                  Open the goal →
                </a>
              )}
            </form>
          )}
        </div>
      </section>
    </Page>
  );
}
