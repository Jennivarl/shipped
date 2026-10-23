"""
Stand-ins for the contracts SHIPPED's suite reads.

Direct mode loads one contract per process, so WATCH, POT and BADGE cannot
be tested against the real GOAL or the real WATCH in the same test. This
answers the cross-contract call with the protocol the chain uses,
dispatching on the method name as separate contracts would, and records
every transfer so a test can assert on money rather than on log lines.
"""

from contracts.releases import epoch_seconds

ORGANISER = b"\xa0" * 20
PAYEE = b"\xb0" * 20
BACKER = b"\xc0" * 20
OTHER = b"\xd0" * 20
STRANGER = b"\xe0" * 20

GOAL_AT = "0x" + ("dd" * 20)
WATCH_AT = "0x" + ("ee" * 20)

NAME = "v2"
GOAL_ID = "0x" + ORGANISER.hex() + ":" + NAME
PACKAGE = "requests"
VERSION = "2.33.0"
URL = "https://pypi.org/pypi/requests/2.33.0/json"
PAYEE_HEX = "0x" + PAYEE.hex()

T_POSTED = "2026-10-20T09:00:00Z"
DEADLINE = epoch_seconds(T_POSTED) + 48 * 3600  # 22 October, 09:00

PLEDGE = 1_000_000

# An EVM transfer, which is how value reaches a plain wallet.
EVM_PAY = "EmitExternalMessage"

CONFIRMED = "2026-10-20T09:30:00Z"
BEFORE = "2026-10-21T09:00:00Z"
AFTER = "2026-10-22T09:00:01Z"


class Stubs:
    """One hook answering for GOAL and WATCH."""

    def __init__(self):
        self.target = {
            "goal_id": GOAL_ID,
            "organiser": "0x" + ORGANISER.hex(),
            "name": NAME,
            "registry": "pypi",
            "package": PACKAGE,
            "version": VERSION,
            "url": URL,
            "payee": PAYEE_HEX,
            "posted_at": T_POSTED,
            "deadline": str(DEADLINE),
        }
        # The usual case: the network has confirmed the version is not out.
        self.state = {
            "goal_id": GOAL_ID,
            "absent_at": CONFIRMED,
            "closed": "",
            "shipped": False,
            "in_time": False,
            "shipped_at": "",
            "deadline": str(DEADLINE),
            "checks": "0",
            "last_at": "",
            "last_verdict": "",
            "last_note": "",
        }
        self.transfers = []

    def set_target(self, **changes):
        self.target = {**self.target, **changes}
        return self

    def shipped_in_time(self):
        self.state = {**self.state, "shipped": True, "in_time": True, "shipped_at": BEFORE,
                      "last_verdict": "shipped", "last_note": "the release names this payee"}
        return self

    def unconfirmed(self):
        """Nobody has yet had the network confirm the version is not out."""
        self.state = {**self.state, "absent_at": ""}
        return self

    def already_existed(self):
        """The first reading found the version already published."""
        self.state = {**self.state, "absent_at": "", "closed": "existed", "last_verdict": "shipped",
                      "last_note": "the release names this payee"}
        return self

    def came_out_unclaimed(self):
        """Confirmed absent, then published without naming the payee."""
        self.state = {**self.state, "closed": "unclaimed", "last_verdict": "unclaimed",
                      "last_note": "the release does not name this payee"}
        return self

    def install(self, vm):
        def hook(_vm, request):
            from gltest.direct.sdk_compat import import_calldata

            calldata = import_calldata()
            for kind in ("PostMessage", "EthSend", EVM_PAY):
                if kind in request:
                    msg = request[kind]
                    self.transfers.append(
                        {"to": bytes(msg["address"].as_bytes), "value": int(msg["value"]), "kind": kind}
                    )
                    return {"ok": None}
            if "CallContract" not in request:
                return None
            method = request["CallContract"]["calldata"][""]
            answer = self.state if method == "status" else self.target
            return bytes([0]) + calldata.encode(answer)

        vm._gl_call_hook = hook
        return self
