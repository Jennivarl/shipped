/**
 * Everything the site reads from the chain, and the formatting around it.
 *
 * Reads go straight to Studio Next from the browser with no server in
 * between, so what the page shows is what the contracts say, not a copy that
 * could go stale.
 */

export const GOAL = "0x11CE3247F16569C42031F6FE3Dedf07027C1088e";
export const WATCH = "0xeaAC1bC201E35fB2eF7995fA5B96FA5B425D0B74";
export const POT = "0x5aA0C16F41Ba65952c76Bb27302849F3EA0FC4a4";

export const RPC = "https://studio-next.genlayer.com/api";
export const EXPLORER = "https://explorer-studio-dev.genlayer.com";
export const CHAIN_ID = 61997;
export const CHAIN_NAME = "GenLayer Studio Next";
export const REPO = "https://github.com/Jennivarl/shipped";

/**
 * genlayer-js ships Studio's dev network with another RPC and id, so the
 * site takes its contract settings and points them at Studio Next.
 */
export async function studioNext() {
  const { studioDevnet } = await import("genlayer-js/chains");
  return {
    ...studioDevnet,
    id: CHAIN_ID,
    name: CHAIN_NAME,
    rpcUrls: { default: { http: [RPC] } },
    blockExplorers: { default: { name: "Studio Next Explorer", url: EXPLORER } },
  };
}

export const addressUrl = (a: string) => `${EXPLORER}/address/${a}`;
export const txUrl = (tx: string) => `${EXPLORER}/tx/${tx}`;

export type Goal = {
  goal_id: string;
  organiser: string;
  name: string;
  registry: "pypi" | "npm";
  package: string;
  version: string;
  url: string;
  payee: string;
  posted_at: string;
  deadline: string;
};

export type Status = {
  goal_id: string;
  shipped: boolean;
  in_time: boolean;
  shipped_at: string;
  deadline: string;
  checks: string;
  last_at: string;
  last_verdict: string;
  last_note: string;
};

export type Fund = {
  goal_id: string;
  payee: string;
  total: string;
  backers: string;
  state: string;
  claimed_at: string;
};

export type GoalView = { goal: Goal; status: Status; fund: Fund | null };

let reader: Promise<{ read: (a: string, f: string, args?: unknown[]) => Promise<unknown> }> | null = null;

/** One read-only client for the whole page, created on first use. */
function client() {
  if (!reader) {
    reader = (async () => {
      const [{ createClient }, chain] = await Promise.all([import("genlayer-js"), studioNext()]);
      const c = createClient({ chain: chain as never });
      return {
        read: (address: string, functionName: string, args: unknown[] = []) =>
          c.readContract({ address: address as `0x${string}`, functionName, args: args as never[] }),
      };
    })();
  }
  return reader;
}

/**
 * Studio Next runs at most 8 contract reads at once across all its visitors
 * and answers "server busy" beyond that, so the page keeps no more than 4 in
 * flight and tries a busy read again after a short pause.
 */
const MAX_IN_FLIGHT = 4;
let inFlight = 0;
const waiting: (() => void)[] = [];

async function slot<T>(work: () => Promise<T>): Promise<T> {
  if (inFlight >= MAX_IN_FLIGHT) await new Promise<void>((r) => waiting.push(r));
  inFlight++;
  try {
    return await work();
  } finally {
    inFlight--;
    waiting.shift()?.();
  }
}

const busy = (e: unknown) => /execution slots|server busy/i.test(String((e as Error)?.message ?? e));

async function read<T>(address: string, fn: string, args: unknown[] = []): Promise<T> {
  const c = await client();
  for (let attempt = 1; ; attempt++) {
    try {
      return (await slot(() => c.read(address, fn, args))) as T;
    } catch (e) {
      if (!busy(e) || attempt === 4) throw e;
      await new Promise((r) => setTimeout(r, 1500 * attempt));
    }
  }
}

/**
 * A read the contract itself refused ("never staked", "nobody pledged")
 * reaches the browser only as "execution failed". That alone means
 * "nothing there"; a rate limit or a dropped connection is still an error,
 * so it is thrown rather than shown as zero.
 */
function absent<T>(fallback: T) {
  return (e: unknown): T => {
    if (/execution failed/i.test(String((e as Error)?.message ?? e))) return fallback;
    throw e;
  };
}

export const readGoalIds = () => read<string[]>(GOAL, "goal_list");

export async function readGoal(id: string): Promise<GoalView> {
  const [goal, status, fund] = await Promise.all([
    read<Goal>(GOAL, "get", [id]),
    read<Status>(WATCH, "status", [id]),
    // A goal nobody has backed has no fund yet, and the pot says so by
    // raising. That is "zero pledged", not a failure to read.
    read<Fund>(POT, "get_fund", [id]).catch(absent<Fund | null>(null)),
  ]);
  return { goal, status, fund };
}

/** The newest goals, capped so one page view stays well inside the RPC's per-minute allowance. */
export async function readGoals(limit = 6): Promise<GoalView[]> {
  const ids = (await readGoalIds()).slice(-limit);
  const views = await Promise.all(ids.map((id) => readGoal(id).catch(absent<GoalView | null>(null))));
  return views.filter((v): v is GoalView => v !== null).reverse();
}

export async function readPledged(id: string, backer: string): Promise<bigint> {
  return BigInt(await read<string>(POT, "pledged", [id, backer]).catch(absent("0")));
}

export async function readBalance(address: string): Promise<bigint> {
  const res = await fetch(RPC, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_getBalance", params: [address, "latest"] }),
  });
  const body = (await res.json()) as { result?: string };
  return BigInt(body.result ?? "0x0");
}

/**
 * 1 means the call returned normally, 2 means the contract raised. Studio
 * Next has no gen_getTransactionReceipt; the transaction itself carries it.
 */
export async function txOutcome(txId: string): Promise<{ execution: number | null }> {
  const res = await fetch(RPC, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_getTransactionByHash", params: [txId] }),
  });
  const body = (await res.json()) as { result?: { txExecutionResult?: number } };
  return { execution: body?.result?.txExecutionResult ?? null };
}

// ------------------------------------------------------------------
// what a goal's state means, in one word
// ------------------------------------------------------------------

export type Phase = "open" | "shipped" | "paid" | "missed";

export function phase(v: GoalView, nowSeconds: number): Phase {
  if (v.fund?.state === "claimed") return "paid";
  if (v.status.in_time) return "shipped";
  if (nowSeconds > Number(v.goal.deadline)) return "missed";
  return "open";
}

export const PHASE_LABEL: Record<Phase, string> = {
  open: "Waiting on the release",
  shipped: "Shipped in time",
  paid: "Paid to the maintainer",
  missed: "Deadline missed, refunds open",
};

// ------------------------------------------------------------------
// formatting
// ------------------------------------------------------------------

const WEI = 10n ** 18n;

/** Wei to GEN, truncated, never rounded up. */
export function gen(wei: string | bigint, decimals = 2): string {
  const v = typeof wei === "bigint" ? wei : BigInt(wei || "0");
  const whole = v / WEI;
  const frac = (v % WEI).toString().padStart(18, "0").slice(0, decimals);
  const w = whole.toLocaleString("en-US");
  return decimals > 0 ? `${w}.${frac}` : w;
}

/** GEN typed by a person to wei, with BigInt only. */
export function toWei(text: string): bigint {
  const t = text.trim();
  if (!/^\d*\.?\d*$/.test(t) || t === "" || t === ".") throw new Error("Enter an amount in GEN.");
  const [w, f = ""] = t.split(".");
  if (f.length > 18) throw new Error("GEN has 18 decimals at most.");
  return BigInt(w || "0") * WEI + BigInt((f + "0".repeat(18)).slice(0, 18));
}

export const short = (a: string, head = 6, tail = 4) =>
  a && a.length > head + tail ? `${a.slice(0, head)}…${a.slice(-tail)}` : a;

export const nowSeconds = () => Math.floor(Date.now() / 1000);

/** "in 2 days", "3 hours ago": how far a deadline is from now. */
export function until(seconds: number, now = nowSeconds()): string {
  const d = seconds - now;
  const a = Math.abs(d);
  const unit = a >= 86400 ? [Math.round(a / 86400), "day"] : a >= 3600 ? [Math.round(a / 3600), "hour"] : [Math.max(1, Math.round(a / 60)), "minute"];
  const text = `${unit[0]} ${unit[1]}${unit[0] === 1 ? "" : "s"}`;
  return d >= 0 ? `in ${text}` : `${text} ago`;
}

export function dateTime(seconds: number): string {
  return new Date(seconds * 1000).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

export const registryHome = (g: Goal) =>
  g.registry === "pypi" ? `https://pypi.org/project/${g.package}/` : `https://www.npmjs.com/package/${g.package}`;
