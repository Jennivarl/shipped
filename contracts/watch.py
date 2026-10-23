# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
"""
WATCH. Whether the release exists, read from the registry under consensus.

    check(goal_id)    one fetch of the version's registry document
    status(goal_id)   shipped or not, when it was first seen, the last word

Every validator fetches the same registry URL, built from the goal's terms,
and agrees with the leader only if the verdict and the reason both match.
Nothing a caller passes reaches the fetch.

Shipping is proven by the network seeing it, at the time it saw it, never
by a date the registry reports or anybody types. The maintainer is the one
who gains from a release being seen, so the maintainer checks the moment
it is out. Only an observation before the deadline counts.

Once shipped is seen, it is final. Further checks are refused, so nothing
that happens to the registry later, a yanked file, an outage, a mirror
serving stale data, can take back a payout that was already earned.

A goal pays only for a release made after the network confirmed it was not
out yet. So the first `not_yet` reading is recorded, and POT accepts no
pledge before it. A version the network finds already published before
that, or published later without naming the payee, closes the goal for
good: published versions are immutable, so it can never become payable.
"""

from dataclasses import dataclass

import genlayer as gl
from genlayer.types import *

from contracts.releases import (
    CLOSED_EXISTED,
    CLOSED_UNCLAIMED,
    NOT_YET,
    SHIPPED,
    UNCLAIMED,
    VERDICTS,
    classify,
    epoch_seconds,
    unreached,
)

_MAX_NOTE = 60


@gl.storage.allow
@dataclass
class Record:
    absent_at: str
    closed: str
    shipped_at: str
    checks: u256
    last_at: str
    last_verdict: str
    last_note: str


class Watch(gl.contract.Contract):
    # The one goal book this watch believes. Fixed at deployment: whoever
    # could name the source of the terms could choose which URL is read.
    goal: Address
    records: gl.storage.TreeMap[str, Record]

    def __init__(self, goal: str):
        self.goal = _address(goal)

    @gl.public.write
    def check(self, goal_id: str) -> dict:
        """
        Ask the registry once. Anyone may; the answer is the network's.
        """
        key = goal_id.strip().lower()
        target = gl.contract.get_at(self.goal).view().get(key)
        if str(target["goal_id"]).lower() != key:
            raise gl.vm.UserError("those terms are about a different goal")

        record = self.records[key] if key in self.records else _blank()
        if record.shipped_at:
            raise gl.vm.UserError("that release has already been seen, and that is final")
        if record.closed:
            raise gl.vm.UserError("that version is already out and can never pay this goal, and that is final")

        now_stamp = _stamp()
        now = epoch_seconds(now_stamp)
        if now is None:
            raise gl.vm.UserError("the clock could not be read")
        if now > int(str(target["deadline"])):
            raise gl.vm.UserError("the deadline has passed, so nothing seen now could count")

        url = str(target["url"])
        version = str(target["version"])
        payee = str(target["payee"])

        def leader_fn():
            return _read(url, version, payee)

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            leader = leaders_res.calldata
            if not isinstance(leader, dict):
                return False
            mine = _read(url, version, payee)
            return leader.get("verdict") == mine["verdict"] and leader.get("note") == mine["note"]

        agreed = gl.vm.run_nondet(leader_fn, validator_fn)
        verdict = str(agreed["verdict"])
        note = str(agreed["note"])
        if verdict not in VERDICTS or not note or len(note) > _MAX_NOTE:
            raise gl.vm.UserError("a reading no fetch could produce")

        record.checks = record.checks + 1
        record.last_at = now_stamp
        record.last_verdict = verdict
        record.last_note = note
        if verdict == NOT_YET and not record.absent_at:
            record.absent_at = now_stamp
        elif verdict in (SHIPPED, UNCLAIMED):
            if not record.absent_at:
                # Out before anyone confirmed it absent: not a release this
                # goal could have paid for, whoever it names.
                record.closed = CLOSED_EXISTED
            elif verdict == SHIPPED:
                record.shipped_at = now_stamp
            else:
                record.closed = CLOSED_UNCLAIMED
        self.records[key] = record
        return _as_dict(key, record, int(str(target["deadline"])))

    @gl.public.view
    def status(self, goal_id: str) -> dict:
        """
        What a consumer reads. `in_time` is the only field that moves money,
        and it is true only for a release seen before the deadline.
        """
        key = goal_id.strip().lower()
        target = gl.contract.get_at(self.goal).view().get(key)
        record = self.records[key] if key in self.records else _blank()
        return _as_dict(key, record, int(str(target["deadline"])))

    @gl.public.view
    def settings(self) -> dict:
        return {"goal": self.goal.as_hex}


def _read(url: str, version: str, payee: str) -> dict:
    """Fetch once and say exactly what the registry said, in primitives."""
    try:
        resp = gl.nondet.web.get(url)
        status = int(resp.status)
        body = (resp.body or b"").decode("utf-8", errors="replace")
    except Exception:
        return unreached()
    return classify(status, body, version, payee)


def _blank() -> Record:
    return Record(absent_at="", closed="", shipped_at="", checks=0, last_at="", last_verdict="", last_note="")


def _stamp() -> str:
    return str(gl.message.raw["datetime"])


def _address(value) -> Address:
    if hasattr(value, "as_hex"):
        return value
    return Address(str(value).strip())


def _as_dict(key: str, record: Record, deadline: int) -> dict:
    seen = epoch_seconds(record.shipped_at) if record.shipped_at else None
    in_time = bool(record.absent_at) and seen is not None and seen <= deadline
    return {
        "goal_id": key,
        "absent_at": record.absent_at,
        "closed": record.closed,
        "shipped": bool(record.shipped_at),
        "in_time": in_time,
        "shipped_at": record.shipped_at,
        "deadline": str(deadline),
        "checks": str(record.checks),
        "last_at": record.last_at,
        "last_verdict": record.last_verdict,
        "last_note": record.last_note,
    }
