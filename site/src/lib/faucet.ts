import { RPC } from "./chain";

/**
 * A new wallet holds no GEN on Studio Next, and nothing can be done with
 * nothing. Studio Next is a devnet with a faucet, so the first time a wallet
 * connects here it is topped up once. Either way it can still read
 * everything.
 */

const KEY = "funded";

function seen(address: string): boolean {
  try {
    return (localStorage.getItem(KEY) ?? "").split(",").includes(address.toLowerCase());
  } catch {
    return false;
  }
}

function remember(address: string) {
  try {
    const list = (localStorage.getItem(KEY) ?? "").split(",").filter(Boolean);
    list.push(address.toLowerCase());
    localStorage.setItem(KEY, list.join(","));
  } catch {
    // Storage can be blocked. The worst case is asking the faucet twice.
  }
}

export async function fundOnce(address: string): Promise<string | null> {
  if (seen(address)) return null;
  try {
    const res = await fetch(RPC, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "sim_fundAccount", params: [address, 5000000000000000000] }),
    });
    const body = (await res.json()) as { result?: string };
    if (typeof body.result === "string") {
      remember(address);
      return body.result;
    }
    return null;
  } catch {
    return null;
  }
}
