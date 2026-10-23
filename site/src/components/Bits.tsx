import type { GoalView, Phase } from "../lib/chain";
import { PHASE_LABEL, dateTime, gen, nowSeconds, phase, txUrl, until } from "../lib/chain";
import type { TxState } from "../lib/hooks";

const PHASE_STYLE: Record<Phase, string> = {
  confirm: "bg-accent-tint text-accent",
  open: "bg-accent-tint text-accent",
  existed: "bg-warn-tint text-warn",
  unclaimed: "bg-warn-tint text-warn",
  shipped: "bg-good-tint text-good",
  paid: "bg-good-tint text-good",
  missed: "bg-warn-tint text-warn",
};

export function PhaseChip({ value }: { value: Phase }) {
  return (
    <span className={`chip ${PHASE_STYLE[value]}`}>
      <i />
      {PHASE_LABEL[value]}
    </span>
  );
}

export function Registry({ name }: { name: string }) {
  return <span className="mono rounded border border-line bg-raise px-1.5 py-0.5 text-[11px] text-body">{name}</span>;
}

/** One release as a row of the table. Every number on it is read from the contracts. */
export function GoalRow({ v }: { v: GoalView }) {
  const p = phase(v, nowSeconds());
  const deadline = Number(v.goal.deadline);
  return (
    <a
      href={`#/goal?id=${encodeURIComponent(v.goal.goal_id)}`}
      className="grid gap-2 border-b border-line px-6 py-4 no-underline transition last:border-0 hover:bg-raise md:grid-cols-[1.4fr_1fr_1fr_1.2fr] md:items-center md:gap-4"
    >
      <div className="flex items-center gap-3">
        <Registry name={v.goal.registry} />
        <span className="mono text-[14.5px] text-ink">
          {v.goal.package}<span className="text-faint">@</span><span className="text-cyan">{v.goal.version}</span>
        </span>
      </div>
      <div className="mono text-[14px] text-ink">
        {gen(v.fund?.total ?? "0")} <span className="text-faint">GEN</span>
      </div>
      <div className="mono text-[13px] text-body">{p === "open" ? until(deadline) : dateTime(deadline)}</div>
      <div>
        <PhaseChip value={p} />
      </div>
    </a>
  );
}

/** What happened to the last thing this page submitted, in words. */
export function TxBanner({ tx, onClose }: { tx: TxState | null; onClose: () => void }) {
  if (!tx) return null;
  const tone =
    tx.state === "done" ? "border-good bg-good-tint text-good" : tx.state === "failed" || tx.state === "unsent" ? "border-warn bg-warn-tint text-warn" : "border-accent bg-accent-tint text-accent";
  const word = tx.state === "done" ? "Done" : tx.state === "failed" ? "Refused" : tx.state === "unsent" ? "Not sent" : "Processing";
  return (
    <div className={`mono mt-5 flex items-start justify-between gap-4 rounded-lg border px-4 py-3 text-[13px] ${tone}`}>
      <div>
        <span className="font-extrabold">{word}:</span> {tx.label}
        {tx.detail ? <span> — {tx.detail}</span> : null}
        {tx.hash ? (
          <a href={txUrl(tx.hash)} target="_blank" rel="noreferrer" className="ml-2 font-bold underline">
            view transaction
          </a>
        ) : null}
      </div>
      <button type="button" onClick={onClose} className="font-bold opacity-70 hover:opacity-100" aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}

export function Spinner({ label = "Reading the chain" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-[14px] text-body">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      {label}
    </div>
  );
}
