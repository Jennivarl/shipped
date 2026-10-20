import { useState } from "react";
import { short } from "../lib/chain";
import { fundOnce } from "../lib/faucet";
import { useAccount } from "../lib/hooks";
import { walletAvailable, walletError } from "../lib/wallet";

/**
 * Connect a browser wallet. The first time a wallet connects it is topped up
 * from the devnet faucet, because an account that cannot transact is worse
 * than none.
 */
function useConnect() {
  const { account, connectWallet } = useAccount();
  const [error, setError] = useState<string | null>(null);
  const go = async () => {
    setError(null);
    try {
      const a = await connectWallet();
      if (a) await fundOnce(a);
    } catch (e) {
      setError(walletError(e));
    }
  };
  return { account, go, error };
}

const INSTALL = "https://metamask.io/download/";

export function Account() {
  const { account, go } = useConnect();
  if (account) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-wash px-3 py-2 text-[13px] font-bold text-ink">
        <span className="h-2 w-2 rounded-full bg-good" />
        <span className="mono">{short(account, 6, 4)}</span>
      </span>
    );
  }
  if (!walletAvailable()) {
    return (
      <a href={INSTALL} target="_blank" rel="noreferrer" className="btn btn-line no-underline">
        Install a wallet
      </a>
    );
  }
  return (
    <button type="button" onClick={go} className="btn btn-line">
      Connect wallet
    </button>
  );
}

/** The same connect, for a page that needs it inside its own layout. */
export function ConnectButton({ label = "Connect wallet" }: { label?: string }) {
  const { go, error } = useConnect();
  if (!walletAvailable()) {
    return (
      <a href={INSTALL} target="_blank" rel="noreferrer" className="btn btn-primary w-full no-underline">
        Install a browser wallet
      </a>
    );
  }
  return (
    <>
      <button type="button" onClick={go} className="btn btn-primary w-full">
        {label}
      </button>
      {error && <p className="mt-3 text-[13px] text-warn">{error}</p>}
    </>
  );
}
