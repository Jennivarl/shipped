import { MESSAGE_ALLOCATION_ROOT_PARENT_INDEX, MessageType, encodeExternalMessageFeeParams } from "genlayer-js";
import { CHAIN_ID, CHAIN_NAME, EXPLORER, GOAL, POT, RPC, WATCH, studioNext } from "./chain";

/**
 * Signing, from the visitor's own browser wallet.
 *
 * The site never asks for a key and never holds funds. Writes return as soon
 * as the transaction is submitted; the caller polls for the outcome, because
 * waiting inside the client inherits a patience shorter than the chain's and
 * reports failures that later turn out to have succeeded.
 */

const CHAIN_ID_HEX = `0x${CHAIN_ID.toString(16)}`;

type Eip1193 = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, handler: (...args: unknown[]) => void) => void;
  removeListener?: (event: string, handler: (...args: unknown[]) => void) => void;
};

const injected = (): Eip1193 | undefined =>
  typeof window === "undefined" ? undefined : (window as unknown as { ethereum?: Eip1193 }).ethereum;

export const walletAvailable = (): boolean => Boolean(injected());

function provider(): Eip1193 {
  const p = injected();
  if (!p) throw new Error("No wallet found in this browser. Install MetaMask or a similar wallet.");
  return p;
}

/** Every part of the page that shows the account, kept in step. */
const listeners = new Set<(account: string | null) => void>();

/**
 * A readable reason, or null when the visitor simply said no (code 4001).
 * viem keeps the useful part in shortMessage, details, metaMessages or a
 * nested cause, so every layer is unwrapped and the first specific lines win.
 */
export function walletError(err: unknown): string | null {
  if ((err as { code?: number })?.code === 4001) return null;
  const seen = new Set<unknown>();
  const parts: string[] = [];
  let node: unknown = err;
  while (node && !seen.has(node)) {
    seen.add(node);
    const e = node as { shortMessage?: string; details?: string; metaMessages?: string[]; cause?: unknown };
    for (const piece of [e.shortMessage, e.details, ...(e.metaMessages ?? [])]) {
      if (typeof piece === "string" && piece.trim() && !parts.includes(piece.trim())) parts.push(piece.trim());
    }
    node = e.cause;
  }
  if (!parts.length) parts.push((err instanceof Error ? err.message : String(err)).replace(/^Error:\s*/, ""));
  const all = parts.join(" ");
  if (/rate limit/i.test(all)) return "Studio Next is limiting requests from this connection (30 a minute, 500 an hour). Wait a minute and try again.";
  if (/execution slots|server busy/i.test(all)) return "Studio Next is busy right now. Wait a few seconds and try again.";
  if (/failed to fetch|fetch failed/i.test(all)) return "Could not reach Studio Next. Check your connection and try again.";
  return parts.slice(0, 3).join(" — ");
}

export async function connect(): Promise<string> {
  const accounts = (await provider().request({ method: "eth_requestAccounts" })) as string[];
  if (!accounts?.length) throw new Error("The wallet returned no accounts.");
  listeners.forEach((l) => l(accounts[0]));
  return accounts[0];
}

export async function currentAccount(): Promise<string | null> {
  if (!walletAvailable()) return null;
  try {
    const accounts = (await provider().request({ method: "eth_accounts" })) as string[];
    return accounts?.[0] ?? null;
  } catch {
    return null;
  }
}

export function onAccountsChanged(handler: (account: string | null) => void): () => void {
  listeners.add(handler);
  const eth = injected();
  const wrapped = (...args: unknown[]) => handler((args[0] as string[] | undefined)?.[0] ?? null);
  eth?.on?.("accountsChanged", wrapped);
  return () => {
    listeners.delete(handler);
    eth?.removeListener?.("accountsChanged", wrapped);
  };
}

/** Move the wallet to Studio Next, adding the network the first time (4902). */
async function ensureChain(): Promise<void> {
  const id = (await provider().request({ method: "eth_chainId" })) as string;
  if (parseInt(id, 16) === CHAIN_ID) return;
  try {
    await provider().request({ method: "wallet_switchEthereumChain", params: [{ chainId: CHAIN_ID_HEX }] });
  } catch (err) {
    if ((err as { code?: number })?.code !== 4902) throw err;
    await provider().request({
      method: "wallet_addEthereumChain",
      params: [
        {
          chainId: CHAIN_ID_HEX,
          chainName: CHAIN_NAME,
          rpcUrls: [RPC],
          nativeCurrency: { name: "GEN Token", symbol: "GEN", decimals: 18 },
          blockExplorerUrls: [EXPLORER],
        },
      ],
    });
  }
}

/**
 * The funded allocation every outgoing payment needs.
 *
 * Paying a wallet is an external message, and a transaction that does not
 * reserve a budget for one dies with `out_of message_fee total # external`.
 * It is priced with the generic estimator: the per-write estimator accepts
 * the allocation and still reports no message fee, which fails the same way.
 */
function payouts(recipients: string[]) {
  const gas = 200000n;
  const price = 400000000n;
  return recipients.map((to) => ({
    messageType: MessageType.External,
    onAcceptance: false,
    parentIndex: MESSAGE_ALLOCATION_ROOT_PARENT_INDEX,
    recipient: to as `0x${string}`,
    budget: gas * price,
    feeParams: encodeExternalMessageFeeParams({ gasLimit: gas, maxGasPrice: price }),
  }));
}

async function write(address: string, functionName: string, args: unknown[], value = 0n, payTo: string[] = []): Promise<string> {
  await ensureChain();
  const account = (await currentAccount()) ?? (await connect());
  const [{ createClient }, chain] = await Promise.all([import("genlayer-js"), studioNext()]);
  // The account MUST stay a plain address string: genlayer-js signs through
  // the browser wallet only when `config.account` is not an object.
  const client = createClient({ chain: chain as never, account: account as `0x${string}`, provider: provider() as never });
  const callArgs = args as never[];
  const allocations = payTo.length ? payouts(payTo) : undefined;

  let fees: Record<string, unknown> | undefined;
  try {
    if (allocations) {
      const priced = await client.estimateTransactionFees({ messageAllocations: allocations } as never);
      fees = { distribution: priced.distribution, messageAllocations: allocations, feeValue: priced.feeValue };
    } else {
      const est = await client.estimateTransactionFeesForWrite({ address: address as `0x${string}`, functionName, args: callArgs, value });
      fees = { distribution: est.distribution, messageAllocations: est.messageAllocations ?? [], feeValue: est.feeValue };
    }
  } catch {
    // The per-write estimate simulates the call and refuses one that would
    // raise; the generic one does not simulate. A fee is always sent, because
    // the consensus contract rejects a zero one.
    try {
      const base = await client.estimateTransactionFees((allocations ? { messageAllocations: allocations } : {}) as never);
      fees = { distribution: base.distribution, messageAllocations: allocations ?? [], feeValue: base.feeValue };
    } catch {
      fees = undefined;
    }
  }

  try {
    const hash = await client.writeContract({
      address: address as `0x${string}`,
      functionName,
      args: callArgs,
      value,
      ...(fees ? { fees: fees as never } : {}),
    });
    return String(hash);
  } catch (e) {
    const detail = walletError(e);
    if (detail === null) throw new Error("Cancelled in the wallet.");
    throw new Error(detail);
  }
}

// ------------------------------------------------------------------
// what the site can do
// ------------------------------------------------------------------

export const postGoal = (name: string, registry: string, pkg: string, version: string, payee: string, hours: number) =>
  write(GOAL, "post", [name, registry, pkg, version, payee, hours]);

export const pledge = (goalId: string, amountWei: bigint) => write(POT, "pledge", [goalId], amountWei);

export const check = (goalId: string) => write(WATCH, "check", [goalId]);

/** Pays the payee, so it reserves one payment for them. */
export const claim = (goalId: string, payee: string) => write(POT, "claim", [goalId], 0n, [payee]);

/** Pays the caller back, so it reserves one payment for them. */
export const refund = (goalId: string, backer: string) => write(POT, "refund", [goalId], 0n, [backer]);
