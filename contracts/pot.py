# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
"""
POT. The money many backers put toward one release.

    pledge(goal_id)   payable, any number of backers, any number of times
    claim(goal_id)    the payee takes the whole pot, once, if the release
                      was seen in time
    refund(goal_id)   after the deadline, each backer takes back exactly
                      what they put in, if it was not

This contract judges nothing. It holds pledges and reads WATCH, which only
says a release was seen in time if every validator read the registry and
found that version naming this payee before the deadline.

Pledges are commitments: there is no taking one back early. A maintainer
deciding whether to cut a release should be able to count the pot, and a
pledge that can vanish the night before the deadline is not something
anybody can count.

Every pledge has exactly one way out, and they cannot both be open:

    seen in time        claim pays the payee everything
    not seen in time    after the deadline, each backer refunds their own

Refunds are pulled by each backer rather than pushed in a loop, so one
contract call never has to pay an unbounded list of people.
"""

from dataclasses import dataclass

import genlayer as gl
from genlayer.types import *

from contracts.releases import epoch_seconds

STATE_OPEN = "open"
STATE_CLAIMED = "claimed"


@gl.storage.allow
@dataclass
class Fund:
    goal_id: str
    payee: Address
    total: u256
    backers: u256
    state: str
    claimed_at: str


class Pot(gl.contract.Contract):
    # Both fixed at deployment. A caller who could name the terms or the
    # watch could decide whether a release happened.
    goal: Address
    watch: Address
    funds: gl.storage.TreeMap[str, Fund]
    # goal_id + "|" + backer address, to what that backer has outstanding.
    pledges: gl.storage.TreeMap[str, u256]
    fund_ids: gl.storage.DynArray[str]
    committed: u256

    def __init__(self, goal: str, watch: str):
        self.goal = _address(goal)
        self.watch = _address(watch)
        self.committed = 0

    @gl.public.write.payable
    def pledge(self, goal_id: str) -> dict:
        """Put money toward a release, before the deadline and before it ships."""
        key = goal_id.strip().lower()
        amount = int(gl.message.value)
        if amount <= 0:
            raise gl.vm.UserError("send your pledge with this call")

        target = self._target(key)
        now = epoch_seconds(_stamp())
        if now is None:
            raise gl.vm.UserError("the clock could not be read")
        if now > int(str(target["deadline"])):
            raise gl.vm.UserError("the deadline has passed")
        status = self._status(key)
        if bool(status["shipped"]):
            raise gl.vm.UserError("that release has already shipped; the pot is decided")

        if key not in self.funds:
            self.funds[key] = Fund(
                goal_id=key,
                payee=_address(target["payee"]),
                total=0,
                backers=0,
                state=STATE_OPEN,
                claimed_at="",
            )
            self.fund_ids.append(key)
        fund = self.funds[key]

        slot = key + "|" + gl.message.sender_address.as_hex.lower()
        before = int(self.pledges[slot]) if slot in self.pledges else 0
        if before == 0:
            fund.backers = fund.backers + 1
        self.pledges[slot] = before + amount
        fund.total = fund.total + amount
        self.funds[key] = fund
        self.committed = self.committed + amount
        return _as_dict(key, fund)

    @gl.public.write
    def claim(self, goal_id: str) -> dict:
        """
        Pay the payee everything, once the release was seen in time.

        Anyone may call it: the payee is fixed in the goal, and whether the
        release counts is WATCH's reading of the registry, not the caller's.
        """
        key = goal_id.strip().lower()
        fund = self._open(key)
        status = self._status(key)
        if not bool(status["in_time"]):
            raise gl.vm.UserError("the release has not been seen in time")
        total = int(fund.total)
        fund.state = STATE_CLAIMED
        fund.claimed_at = _stamp()
        self.funds[key] = fund
        self.committed = self.committed - total
        # State first, then value.
        _pay(fund.payee, total)
        return _as_dict(key, fund)

    @gl.public.write
    def refund(self, goal_id: str) -> dict:
        """
        Take back your own pledge, after a deadline the release missed.
        """
        key = goal_id.strip().lower()
        fund = self._open(key)
        target = self._target(key)
        now = epoch_seconds(_stamp())
        if now is None:
            raise gl.vm.UserError("the clock could not be read")
        if now <= int(str(target["deadline"])):
            raise gl.vm.UserError("the deadline has not passed yet")
        status = self._status(key)
        if bool(status["in_time"]):
            raise gl.vm.UserError("the release was seen in time, so the pot belongs to the payee")

        backer = gl.message.sender_address
        slot = key + "|" + backer.as_hex.lower()
        owed = int(self.pledges[slot]) if slot in self.pledges else 0
        if owed <= 0:
            raise gl.vm.UserError("you have nothing pledged to this goal")
        self.pledges[slot] = 0
        fund.total = fund.total - owed
        self.funds[key] = fund
        self.committed = self.committed - owed
        _pay(backer, owed)
        return {**_as_dict(key, fund), "refunded": str(owed), "to": backer.as_hex}

    @gl.public.view
    def get_fund(self, goal_id: str) -> dict:
        key = goal_id.strip().lower()
        if key not in self.funds:
            raise gl.vm.UserError("nobody has pledged to " + key)
        return _as_dict(key, self.funds[key])

    @gl.public.view
    def pledged(self, goal_id: str, backer: str) -> str:
        slot = goal_id.strip().lower() + "|" + _address(backer).as_hex.lower()
        return str(self.pledges[slot]) if slot in self.pledges else "0"

    @gl.public.view
    def fund_list(self) -> list:
        return [f for f in self.fund_ids]

    @gl.public.view
    def reserves(self) -> dict:
        return {"committed": str(self.committed)}

    @gl.public.view
    def settings(self) -> dict:
        return {"goal": self.goal.as_hex, "watch": self.watch.as_hex}

    def _target(self, key: str) -> dict:
        target = gl.contract.get_at(self.goal).view().get(key)
        if str(target["goal_id"]).lower() != key:
            raise gl.vm.UserError("those terms are about a different goal")
        return target

    def _status(self, key: str) -> dict:
        status = gl.contract.get_at(self.watch).view().status(key)
        if str(status["goal_id"]).lower() != key:
            raise gl.vm.UserError("that status is about a different goal")
        return status

    def _open(self, key: str) -> Fund:
        if key not in self.funds:
            raise gl.vm.UserError("nobody has pledged to " + key)
        fund = self.funds[key]
        if fund.state != STATE_OPEN:
            raise gl.vm.UserError("that pot is already " + fund.state)
        return fund


def _stamp() -> str:
    return str(gl.message.raw["datetime"])


def _address(value) -> Address:
    if hasattr(value, "as_hex"):
        return value
    return Address(str(value).strip())


@gl.evm.contract_interface
class _Wallet:
    """A plain account on the EVM side: nothing to call, only to pay."""

    class View:
        pass

    class Write:
        pass


def _pay(to: Address, amount: int) -> None:
    """
    The one place value leaves this contract.

    Through the EVM interface, which is what reaches a plain wallet. The
    transaction must also reserve a funded allocation for that outgoing
    message.
    """
    _Wallet(to).emit_transfer(value=amount)


def _as_dict(key: str, fund: Fund) -> dict:
    return {
        "goal_id": key,
        "payee": fund.payee.as_hex,
        "total": str(fund.total),
        "backers": str(fund.backers),
        "state": fund.state,
        "claimed_at": fund.claimed_at,
    }
