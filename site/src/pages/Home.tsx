import { useEffect } from "react";
import { GoalRow, PhaseChip, Spinner } from "../components/Bits";
import { Page } from "../components/Layout";
import type { GoalView } from "../lib/chain";
import { REPO, gen, nowSeconds, phase, readGoals, short, until } from "../lib/chain";
import { usePolled } from "../lib/hooks";

function useSectionScroll(ready: boolean) {
  useEffect(() => {
    const section = window.location.hash.split("#")[2];
    if (section) document.getElementById(section)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [ready]);
}

/** What the registry said last, as the terminal prints it. */
function lastReply(v: GoalView): { code: string; text: string; tone: string } {
  switch (v.status.last_verdict) {
    case "shipped":
      return { code: "200", text: "lists this version, names the payee", tone: "text-accent" };
    case "unclaimed":
      return { code: "200", text: "released, but does not name the payee", tone: "text-warn" };
    case "not_yet":
      return { code: "404", text: "no such version yet", tone: "text-warn" };
    case "unknown":
      return { code: "···", text: v.status.last_note, tone: "text-faint" };
    default:
      return { code: "···", text: "not checked yet", tone: "text-faint" };
  }
}

/** The product, live: one goal as the network actually sees it. */
function Terminal({ v }: { v?: GoalView }) {
  const reply = v ? lastReply(v) : null;
  return (
    <div className="term overflow-hidden rounded-[14px] border border-line shadow-[0_30px_70px_-30px_rgba(14,26,20,0.55)]">
      <div className="flex items-center gap-2 border-b border-line bg-raise px-4 py-3">
        <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
        <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
        <span className="h-3 w-3 rounded-full bg-[#28c840]" />
        <span className="mono ml-3 text-[12px] text-faint">genlayer · watch</span>
      </div>
      <div className="mono space-y-2.5 px-5 py-5 text-[13.5px] leading-relaxed">
        {v && reply ? (
          <>
            <div>
              <span className="text-accent">$</span> <span className="text-body">shipped watch</span>{" "}
              <span className="text-ink">{v.goal.package}</span> <span className="text-cyan">{v.goal.version}</span>
            </div>
            <div className="text-faint">→ GET {v.goal.url.replace("https://", "")}</div>
            <div className={reply.tone}>
              ← {reply.code} <span className="text-body">{reply.text}</span>
            </div>
            <div className="border-t border-dashed border-line pt-3 text-body">
              <div className="flex justify-between gap-4">
                <span>pot</span>
                <span className="text-ink">
                  {gen(v.fund?.total ?? "0")} GEN · {v.fund?.backers ?? "0"} backer{v.fund?.backers === "1" ? "" : "s"}
                </span>
              </div>
              <div className="flex justify-between gap-4">
                <span>pays</span>
                <span className="text-ink">{short(v.goal.payee, 6, 4)}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span>deadline</span>
                <span className="text-ink">{until(Number(v.goal.deadline))}</span>
              </div>
            </div>
            <div className="flex items-center justify-between pt-2">
              <PhaseChip value={phase(v, nowSeconds())} />
              <a href={`#/goal?id=${encodeURIComponent(v.goal.goal_id)}`} className="btn btn-primary px-4 py-2 text-[13px] no-underline">
                Back it →
              </a>
            </div>
          </>
        ) : (
          <div className="caret text-body">reading the contracts</div>
        )}
      </div>
    </div>
  );
}

const PIPELINE = [
  ["post", "Anyone posts a goal", "A package, the exact version, a deadline, and who gets paid. The network first confirms that version is not out yet."],
  ["pledge", "Backers pledge", "Any number of them, any amount, once it is confirmed missing. Pledges cannot be pulled early, so a maintainer can count on them."],
  ["check", "The network reads the registry", "Every validator fetches the version's own page on PyPI or npm: a 200 naming the payee, or a 404."],
  ["settle", "Paid, or refunded", "Seen in time, the pot goes to the maintainer. Missed, every backer takes back exactly what they put in."],
];

export default function Home() {
  const goals = usePolled(readGoals, 300000);
  useSectionScroll(Boolean(goals.data));
  const live = goals.data?.find((v) => phase(v, nowSeconds()) === "open") ?? goals.data?.[0];

  return (
    <Page>
      {/* ---- hero ---- */}
      <section className="relative overflow-hidden">
        <div className="grid-bg pointer-events-none absolute inset-0" />
        <div className="relative mx-auto grid max-w-[1180px] items-center gap-12 px-5 pb-24 pt-16 lg:grid-cols-[1.2fr_1fr] lg:pt-24">
          <div>
            <div className="mono inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-[12px] text-body">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" /> pypi · npm · settled on GenLayer
            </div>
            <h1 className="mt-7 text-[46px] font-bold leading-[1.02] tracking-[-0.035em] text-ink sm:text-[62px]">
              Fund the release.
              <br />
              Pay when it <span className="text-accent">ships</span>.
            </h1>
            <p className="mt-6 max-w-[520px] text-[18px] leading-relaxed text-body">
              Back the exact version you are waiting for. The registry decides, not a promise: when that version appears on PyPI
              or npm, naming its maintainer, before the deadline, the pot is theirs. If it doesn't, every backer is refunded.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <a href="#/#goals" className="btn btn-primary no-underline">Back a release</a>
              <a href="#/start" className="btn btn-secondary no-underline">Post a goal</a>
            </div>
            <p className="mono mt-6 text-[12.5px] text-faint">
              any browser wallet · new wallets get test GEN ·{" "}
              <a href={REPO} target="_blank" rel="noreferrer" className="text-body hover:text-accent">
                read the contracts
              </a>
            </p>
          </div>
          <Terminal v={live} />
        </div>
      </section>

      {/* ---- how ---- */}
      <section id="how" className="border-y border-line bg-wash py-24">
        <div className="mx-auto max-w-[1180px] px-5">
          <div className="mono text-[12.5px] text-accent">// how it works</div>
          <h2 className="mt-3 max-w-[680px] text-[40px] font-bold leading-tight tracking-tight text-ink">
            Paid by the registry, not by a promise.
          </h2>
          <div className="mt-12 grid gap-px overflow-hidden rounded-[14px] border border-line bg-line md:grid-cols-4">
            {PIPELINE.map(([step, title, body], i) => (
              <div key={step} className="bg-surface p-6">
                <div className="mono flex items-center gap-2 text-[12px] text-faint">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full border border-accent text-[11px] text-accent">{i + 1}</span>
                  {step}
                </div>
                <div className="mt-5 text-[18px] font-semibold text-ink">{title}</div>
                <p className="mt-2 text-[14.5px] leading-relaxed text-body">{body}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-6 rounded-[14px] border border-accent/25 bg-accent-tint p-8 md:grid-cols-[1fr_1.3fr] md:items-center">
            <div>
              <div className="mono text-[12.5px] text-accent">// why nobody can steal the pot</div>
              <div className="mt-2 text-[26px] font-bold leading-tight text-ink">The release has to name who gets paid.</div>
            </div>
            <p className="text-[15px] leading-relaxed text-body">
              Anyone can post a goal, so anyone could name themselves as the maintainer of a popular package and wait for the real
              team to ship. So a release only counts if its own registry metadata carries the payee's address: the README on PyPI,
              or <span className="mono text-ink">"funding"</span> in package.json on npm. Published versions can't be edited, so only
              someone who can publish the package can direct the money.
            </p>
          </div>
        </div>
      </section>

      {/* ---- releases ---- */}
      <section id="goals" className="mx-auto max-w-[1180px] px-5 pt-24">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="mono text-[12.5px] text-accent">// releases being backed</div>
            <h2 className="mt-3 text-[40px] font-bold tracking-tight text-ink">Latest goals</h2>
            <p className="mt-1 text-[15px] text-body">Read live from the contracts every five minutes.</p>
          </div>
          <a href="#/start" className="btn btn-secondary no-underline">Post a goal</a>
        </div>
        <div className="card mt-8 overflow-hidden">
          <div className="mono hidden grid-cols-[1.4fr_1fr_1fr_1.2fr] gap-4 border-b border-line bg-raise px-6 py-3 text-[11.5px] uppercase tracking-wider text-faint md:grid">
            <span>release</span>
            <span>pot</span>
            <span>deadline</span>
            <span>status</span>
          </div>
          {goals.data?.map((v) => <GoalRow key={v.goal.goal_id} v={v} />)}
          {goals.loading && <div className="px-6 py-6"><Spinner /></div>}
          {goals.error && !goals.data && <p className="px-6 py-6 text-warn">Could not read the contracts: {goals.error}</p>}
          {goals.data && goals.data.length === 0 && <p className="px-6 py-6 text-body">No goals yet. Post the first.</p>}
        </div>
      </section>
    </Page>
  );
}
