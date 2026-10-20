import { useEffect, useState } from "react";
import { txOutcome } from "./chain";
import { connect, currentAccount, onAccountsChanged, walletError } from "./wallet";

export type Polled<T> = {
  data?: T;
  /** Set when the latest attempt failed. Earlier data is kept, not wiped. */
  error?: string;
  loading: boolean;
};

const message = (e: unknown) => walletError(e) ?? "Cancelled in the wallet.";

/**
 * Read something from the chain now, then again every `intervalMs`.
 *
 * Studio Next allows each visitor 30 requests a minute and 500 an hour, so polling is
 * deliberately slow and stops entirely while the tab is in the background;
 * coming back to the tab reads again at once, and a finished transaction
 * calls `refresh` rather than waiting for the next tick.
 *
 * A failed read keeps the last good value and records the error, because
 * "unknown right now" and "zero" are different facts and the page must never
 * show one as the other.
 */
export function usePolled<T>(fetcher: () => Promise<T>, intervalMs = 45000, deps: unknown[] = []): Polled<T> & { refresh: () => void } {
  const [state, setState] = useState<Polled<T>>({ loading: true });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const schedule = (ms = intervalMs) => {
      if (alive && ms > 0) timer = setTimeout(run, ms);
    };
    const run = async () => {
      if (document.hidden) return schedule();
      try {
        const data = await fetcher();
        if (alive) setState({ data, loading: false });
      } catch (e) {
        if (alive) setState((s) => ({ ...s, error: message(e), loading: false }));
        // A read that failed (usually the rate limit) is tried again soon,
        // so a page never sits on numbers from before a transaction.
        return schedule(intervalMs > 0 ? Math.min(intervalMs, 15000) : 15000);
      }
      schedule();
    };
    const onVisible = () => {
      if (!document.hidden && alive) {
        if (timer) clearTimeout(timer);
        run();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    run();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { ...state, refresh: () => setTick((t) => t + 1) };
}

/** The connected account, kept in step with the wallet itself. */
export function useAccount() {
  const [account, setAccount] = useState<string | null>(null);
  useEffect(() => {
    currentAccount().then(setAccount);
    return onAccountsChanged(setAccount);
  }, []);
  const connectWallet = async () => {
    const a = await connect();
    setAccount(a);
    return a;
  };
  return { account, connectWallet };
}

export type TxState = { hash: string; label: string; state: "pending" | "done" | "failed" | "unsent"; detail?: string };

/**
 * Submit a write and follow it to a verdict.
 *
 * "Submitted" is not "done": a transaction can finalize and still have the
 * contract refuse it, which the chain records as execution result 2. Both
 * are shown, so a refusal reads as a refusal rather than as success.
 */
export function useTx(onDone?: () => void) {
  const [tx, setTx] = useState<TxState | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async (label: string, send: () => Promise<string>) => {
    setBusy(true);
    try {
      const hash = await send();
      setTx({ hash, label, state: "pending" });
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => setTimeout(r, 8000));
        const { execution } = await txOutcome(hash).catch(() => ({ execution: null }));
        // 1 returned, 2 the contract raised; anything else is not decided yet.
        if (execution === 1 || execution === 2) {
          setTx({ hash, label, state: execution === 1 ? "done" : "failed", detail: execution === 1 ? undefined : "the contract refused it" });
          // Read again now, and once more shortly after, in case the
          // first read lands before the new state is served.
          onDone?.();
          setTimeout(() => onDone?.(), 6000);
          return;
        }
      }
      setTx({ hash, label, state: "pending", detail: "still processing; check the explorer" });
    } catch (e) {
      // Nothing reached the chain, so nothing was refused: say it was not sent.
      setTx({ hash: "", label, state: "unsent", detail: message(e) });
    } finally {
      setBusy(false);
    }
  };
  return { tx, busy, run, clear: () => setTx(null) };
}
