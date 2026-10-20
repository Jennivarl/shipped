import { useState } from "react";
import { PhaseChip, Registry, Spinner, TxBanner } from "../components/Bits";
import { ConnectButton } from "../components/Account";
import { Page } from "../components/Layout";
import {
  addressUrl,
  dateTime,
  gen,
  nowSeconds,
  phase,
  readBalance,
  readGoal,
  readPledged,
  registryHome,
  toWei,
  until,
} from "../lib/chain";
import { useAccount, usePolled, useTx } from "../lib/hooks";
import { check, claim, pledge, refund } from "../lib/wallet";

function goalId(): string {
  const q = window.location.hash.split("?")[1] ?? "";
  return new URLSearchParams(q).get("id") ?? "";
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line py-3 text-[14.5px] last:border-0">
      <span className="text-body">{k}</span>
      <span className="text-right font-bold text-ink">{children}</span>
    </div>
  );
}

function Actions({ id, view, refresh }: { id: string; view: NonNullable<ReturnType<typeof useView>["data"]>; refresh: () => void }) {
  const { account } = useAccount();
  const signedIn = Boolean(account);
  const [amount, setAmount] = useState("0.05");
  const [error, setError] = useState<string | null>(null);
  const { tx, busy, run, clear } = useTx(refresh);
  const mine = usePolled(() => (account ? readPledged(id, account) : Promise.resolve(0n)), 0, [account, tx?.state]);
  const balance = usePolled(() => (account ? readBalance(account) : Promise.resolve(0n)), 0, [account, tx?.state]);

  const p = phase(view, nowSeconds());
  const pastDeadline = nowSeconds() > Number(view.goal.deadline);

  const go = (label: string, send: () => Promise<string>) => {
    setError(null);
    run(label, send);
  };

  if (!signedIn) {
    return (
      <div className="card p-6">
        <div className="text-[18px] font-extrabold text-ink">Take part</div>
        <p className="mt-2 text-[14.5px] text-body">Connect a wallet to pledge, check the registry, or claim. A new wallet is topped up with test GEN automatically.</p>
        <div className="mt-5"><ConnectButton /></div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <div className="text-[18px] font-extrabold text-ink">Take part</div>
        <div className="text-[13px] text-body">
          Balance <span className="font-bold text-ink">{gen(balance.data ?? 0n, 3)} GEN</span>
        </div>
      </div>

      {p === "open" && (
        <>
          <label className="mt-5 block text-[13px] font-bold text-ink">Pledge, in GEN</label>
          <div className="mt-2 flex gap-2">
            <input className="field" value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" />
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy}
              onClick={() => {
                try {
                  const wei = toWei(amount);
                  if (wei <= 0n) throw new Error("Pledge more than zero.");
                  go(`pledge ${amount} GEN`, () => pledge(id, wei));
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              Pledge
            </button>
          </div>
          <p className="mt-2 text-[12.5px] text-body">A pledge cannot be taken back before the deadline. That is what lets a maintainer count on it.</p>

          <div className="mt-6 border-t border-line pt-5">
            <div className="text-[14px] font-bold text-ink">Has it shipped?</div>
            <p className="mt-1 text-[13px] text-body">
              Ask the network to read the registry now. Anyone can; the maintainer should, the moment it is out.
            </p>
            <button type="button" className="btn btn-secondary mt-3 w-full" disabled={busy} onClick={() => go("check the registry", () => check(id))}>
              Check the registry
            </button>
          </div>
        </>
      )}

      {p === "shipped" && (
        <div className="mt-5">
          <p className="text-[14px] text-body">Seen on the registry in time, naming the payee. The pot is theirs; anyone can send it.</p>
          <button
            type="button"
            className="btn btn-primary mt-4 w-full"
            disabled={busy || !view.fund}
            onClick={() => go(`pay ${gen(view.fund?.total ?? "0")} GEN to the maintainer`, () => claim(id, view.goal.payee))}
          >
            Pay the maintainer
          </button>
        </div>
      )}

      {p === "missed" && (
        <div className="mt-5">
          <p className="text-[14px] text-body">
            The deadline passed without the release being seen. Each backer takes back exactly what they put in.
          </p>
          <div className="mt-3 text-[14px]">
            Your pledge: <span className="font-extrabold">{gen(mine.data ?? 0n, 4)} GEN</span>
          </div>
          <button
            type="button"
            className="btn btn-primary mt-4 w-full"
            disabled={busy || !mine.data || mine.data === 0n}
            onClick={() => go("refund my pledge", () => refund(id, account!))}
          >
            Refund my pledge
          </button>
        </div>
      )}

      {p === "paid" && <p className="mt-5 text-[14px] text-body">Shipped and paid. Nothing left to do here.</p>}

      {p === "open" && !pastDeadline && (mine.data ?? 0n) > 0n && (
        <p className="mt-5 rounded-lg bg-accent-tint px-3 py-2 text-[13px] text-accent">
          You have pledged <span className="font-extrabold">{gen(mine.data ?? 0n, 4)} GEN</span> to this release.
        </p>
      )}
      {error && <p className="mt-4 text-[13.5px] text-warn">{error}</p>}
      <TxBanner tx={tx} onClose={clear} />
    </div>
  );
}

function useView(id: string) {
  return usePolled(() => readGoal(id), 120000, [id]);
}

export default function GoalPage() {
  const id = goalId();
  const view = useView(id);

  return (
    <Page>
      <section className="mx-auto max-w-[1200px] px-5 pt-12">
        <a href="#/#goals" className="text-[14px] font-bold text-accent no-underline">← All releases</a>
        {!view.data && view.loading && <div className="mt-10"><Spinner /></div>}
        {view.error && !view.data && <p className="mt-10 text-warn">Could not read this goal: {view.error}</p>}
        {view.data && (
          <div className="mt-6 grid gap-8 lg:grid-cols-[1.3fr_1fr]">
            <div>
              <div className="flex items-center gap-3">
                <Registry name={view.data.goal.registry} />
                <PhaseChip value={phase(view.data, nowSeconds())} />
              </div>
              <h1 className="mt-4 text-[52px] font-extrabold leading-[1.05] tracking-tight text-ink">
                {view.data.goal.package} <span className="text-accent">{view.data.goal.version}</span>
              </h1>
              <p className="mt-3 text-[17px] text-body">
                Deadline {dateTime(Number(view.data.goal.deadline))} ({until(Number(view.data.goal.deadline))})
              </p>

              <div className="card mt-8 grid gap-6 p-7 sm:grid-cols-3">
                <div>
                  <div className="text-[12px] font-bold uppercase tracking-wide text-faint">In the pot</div>
                  <div className="mt-1 text-[32px] font-extrabold text-accent">{gen(view.data.fund?.total ?? "0")}</div>
                  <div className="text-[13px] text-body">GEN</div>
                </div>
                <div>
                  <div className="text-[12px] font-bold uppercase tracking-wide text-faint">Backers</div>
                  <div className="mt-1 text-[32px] font-extrabold text-ink">{view.data.fund?.backers ?? "0"}</div>
                </div>
                <div>
                  <div className="text-[12px] font-bold uppercase tracking-wide text-faint">Registry checks</div>
                  <div className="mt-1 text-[32px] font-extrabold text-ink">{view.data.status.checks}</div>
                </div>
              </div>

              <div className="card mt-6 p-7">
                <div className="text-[18px] font-extrabold text-ink">The terms</div>
                <div className="mt-3">
                  <Row k="Package">
                    <a href={registryHome(view.data.goal)} target="_blank" rel="noreferrer" className="text-accent">
                      {view.data.goal.package}
                    </a>
                  </Row>
                  <Row k="Exact version">{view.data.goal.version}</Row>
                  <Row k="Paid to">
                    <a href={addressUrl(view.data.goal.payee)} target="_blank" rel="noreferrer" className="mono text-accent">
                      {view.data.goal.payee}
                    </a>
                  </Row>
                  <Row k="The page the network reads">
                    <a href={view.data.goal.url} target="_blank" rel="noreferrer" className="mono break-all text-[12.5px] text-accent">
                      {view.data.goal.url}
                    </a>
                  </Row>
                  <Row k="Last reading">{view.data.status.last_note || "never checked"}</Row>
                  {view.data.status.shipped_at && <Row k="Seen shipped at">{view.data.status.shipped_at.slice(0, 19).replace("T", " ")} UTC</Row>}
                </div>
                <p className="mt-5 rounded-xl bg-wash p-4 text-[13.5px] leading-relaxed text-body">
                  To be paid, the maintainer puts <span className="mono font-bold text-ink">{view.data.goal.payee}</span> in this
                  version's own metadata before publishing: the README on PyPI, or the <span className="mono">funding</span> field on
                  npm. A release that does not name this address does not count, whoever published it.
                </p>
              </div>
            </div>
            <div className="lg:sticky lg:top-24 lg:self-start">
              <Actions id={id} view={view.data} refresh={view.refresh} />
            </div>
          </div>
        )}
      </section>
    </Page>
  );
}
