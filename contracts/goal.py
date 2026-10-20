# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
"""
GOAL. The release being paid for: which package, which version, by when,
and to whom.

    post(name, registry, package, version, payee, hours)
    get(goal_id)

Every term is fixed when the goal is posted. The deadline is the posting
transaction's own time plus the hours given, so nobody types a date, and
the package name is stored in the registry's canonical form, so two
spellings of one package can never become two goals with two pots.

Posting a goal pays nobody and binds nobody. The payee named here only
collects if the released version's own registry metadata names them back,
which WATCH checks and only a publisher of that package can arrange.
"""

from dataclasses import dataclass

import genlayer as gl
from genlayer.types import *

from contracts.releases import (
    MAX_LEAD,
    MIN_LEAD,
    REGISTRIES,
    epoch_seconds,
    normalise_package,
    registry_url,
    valid_package,
    valid_version,
)


@gl.storage.allow
@dataclass
class Target:
    organiser: Address
    name: str
    registry: str
    package: str
    version: str
    payee: Address
    posted_at: str
    deadline: u256


class GoalBook(gl.contract.Contract):
    goals: gl.storage.TreeMap[str, Target]
    goal_ids: gl.storage.DynArray[str]

    def __init__(self):
        pass

    @gl.public.write
    def post(self, name: str, registry: str, package: str, version: str, payee: str, hours: int) -> dict:
        label = name.strip().lower()
        if not label or len(label) > 40:
            raise gl.vm.UserError("name the goal")
        for ch in label:
            if not (("0" <= ch <= "9") or ("a" <= ch <= "z") or ch in "-_"):
                raise gl.vm.UserError("a name is letters, digits, hyphen or underscore")

        reg = registry.strip().lower()
        if reg not in REGISTRIES:
            raise gl.vm.UserError("the registry is pypi or npm")
        if not valid_package(reg, package):
            raise gl.vm.UserError("that is not a package name " + reg + " would accept")
        if not valid_version(version):
            raise gl.vm.UserError("give the version exactly as the registry lists it, like 2.0.0")

        recipient = _address(payee)
        if recipient.as_hex.lower() == "0x" + "00" * 20:
            raise gl.vm.UserError("name a real payee")

        lead = int(hours) * 3600
        if lead < MIN_LEAD or lead > MAX_LEAD:
            raise gl.vm.UserError(f"a deadline is {MIN_LEAD // 3600} hour to {MAX_LEAD // 86400} days away")
        now = epoch_seconds(_stamp())
        if now is None:
            raise gl.vm.UserError("the clock could not be read")

        organiser = gl.message.sender_address
        goal_id = organiser.as_hex.lower() + ":" + label
        if goal_id in self.goals:
            raise gl.vm.UserError("that goal already exists and cannot be changed")

        self.goals[goal_id] = Target(
            organiser=organiser,
            name=label,
            registry=reg,
            package=normalise_package(reg, package),
            version=version.strip(),
            payee=recipient,
            posted_at=_stamp(),
            deadline=now + lead,
        )
        self.goal_ids.append(goal_id)
        return _as_dict(goal_id, self.goals[goal_id])

    @gl.public.view
    def get(self, goal_id: str) -> dict:
        key = goal_id.strip().lower()
        if key not in self.goals:
            raise gl.vm.UserError("no such goal: " + key)
        return _as_dict(key, self.goals[key])

    @gl.public.view
    def goal_list(self) -> list:
        return [g for g in self.goal_ids]


def _stamp() -> str:
    return str(gl.message.raw["datetime"])


def _address(value) -> Address:
    if hasattr(value, "as_hex"):
        return value
    return Address(str(value).strip())


def _as_dict(key: str, target: Target) -> dict:
    return {
        "goal_id": key,
        "organiser": target.organiser.as_hex,
        "name": target.name,
        "registry": target.registry,
        "package": target.package,
        "version": target.version,
        "url": registry_url(target.registry, target.package, target.version),
        "payee": target.payee.as_hex,
        "posted_at": target.posted_at,
        # Seconds since the epoch. Shipping counts only if seen by then.
        "deadline": str(target.deadline),
    }
