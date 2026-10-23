"""
POT run for real in direct mode, against a stand-in GOAL and WATCH.

Every test is about money: who can put it in, who can take it out, when.
The two exits must never both be open, and every pledge must have one.
"""

import sys
from pathlib import Path

import pytest

from test.stubs import (
    AFTER,
    BACKER,
    BEFORE,
    EVM_PAY,
    GOAL_AT,
    GOAL_ID,
    OTHER,
    PAYEE,
    PLEDGE,
    STRANGER,
    WATCH_AT,
    Stubs,
)

BUNDLE = str(Path(__file__).resolve().parent.parent / "contracts" / "pot_bundle.py")


def set_date(vm, stamp):
    vm.warp(stamp)
    message = sys.modules.get("genlayer.message")
    if message is not None and isinstance(getattr(message, "raw", None), dict):
        message.raw["datetime"] = stamp
    gl = sys.modules.get("genlayer.gl")
    if gl is not None and getattr(gl, "message_raw", None) is not None:
        gl.message_raw["datetime"] = stamp


@pytest.fixture
def stubs(direct_vm):
    return Stubs().install(direct_vm)


@pytest.fixture
def pot(direct_vm, direct_deploy, stubs):
    contract = direct_deploy(BUNDLE, goal=GOAL_AT, watch=WATCH_AT)
    direct_vm.strict_mocks = False
    set_date(direct_vm, "2026-10-20T10:00:00Z")
    return contract


def pledge(vm, pot, who=BACKER, amount=PLEDGE):
    vm.value = amount
    try:
        with vm.prank(who):
            return pot.pledge(GOAL_ID)
    finally:
        vm.value = 0


# --------------------------------------------------------------------
# pledging
# --------------------------------------------------------------------


def test_backers_pledge_and_the_pot_adds_up(direct_vm, pot):
    pledge(direct_vm, pot, who=BACKER, amount=PLEDGE)
    got = pledge(direct_vm, pot, who=OTHER, amount=PLEDGE * 2)
    assert got["total"] == str(PLEDGE * 3)
    assert got["backers"] == "2"
    assert pot.reserves()["committed"] == str(PLEDGE * 3)


def test_one_backer_may_pledge_more_than_once(direct_vm, pot):
    pledge(direct_vm, pot)
    got = pledge(direct_vm, pot)
    assert got["backers"] == "1"
    assert pot.pledged(GOAL_ID, "0x" + BACKER.hex()) == str(PLEDGE * 2)


def test_a_pledge_must_carry_money(direct_vm, pot):
    with direct_vm.expect_revert("send your pledge"):
        pledge(direct_vm, pot, amount=0)


def test_nothing_is_pledged_after_the_deadline(direct_vm, pot):
    set_date(direct_vm, AFTER)
    with direct_vm.expect_revert("deadline has passed"):
        pledge(direct_vm, pot)


def test_nothing_is_pledged_once_the_release_has_shipped(direct_vm, pot, stubs):
    stubs.shipped_in_time()
    with direct_vm.expect_revert("already shipped"):
        pledge(direct_vm, pot)


def test_terms_about_another_goal_are_refused(direct_vm, pot, stubs):
    stubs.set_target(goal_id="0x00:other")
    with direct_vm.expect_revert("different goal"):
        pledge(direct_vm, pot)


def test_no_pledge_before_the_network_confirms_the_version_is_not_out(direct_vm, pot, stubs):
    stubs.unconfirmed()
    with direct_vm.expect_revert("check the registry first"):
        pledge(direct_vm, pot)
    assert pot.reserves()["committed"] == "0"


def test_a_release_that_already_existed_cannot_be_funded(direct_vm, pot, stubs):
    """Otherwise anyone could fund a finished release and claim it at once."""
    stubs.already_existed()
    with direct_vm.expect_revert("already out before"):
        pledge(direct_vm, pot)


def test_a_release_that_already_existed_cannot_be_claimed(direct_vm, pot, stubs):
    stubs.already_existed()
    with direct_vm.expect_revert("nobody has pledged"):
        pot.claim(GOAL_ID)
    assert stubs.transfers == []


def test_a_version_out_without_the_payee_takes_no_new_pledges(direct_vm, pot, stubs):
    pledge(direct_vm, pot)
    stubs.came_out_unclaimed()
    with direct_vm.expect_revert("takes no new pledges"):
        pledge(direct_vm, pot, who=OTHER)
    assert pot.get_fund(GOAL_ID)["total"] == str(PLEDGE)


# --------------------------------------------------------------------
# claiming
# --------------------------------------------------------------------


def test_a_release_seen_in_time_pays_the_payee_everything(direct_vm, pot, stubs):
    pledge(direct_vm, pot, who=BACKER)
    pledge(direct_vm, pot, who=OTHER, amount=PLEDGE * 2)
    stubs.shipped_in_time()
    got = pot.claim(GOAL_ID)
    assert got["state"] == "claimed"
    assert stubs.transfers == [{"to": PAYEE, "value": PLEDGE * 3, "kind": EVM_PAY}]
    assert pot.reserves()["committed"] == "0"


def test_the_payee_can_claim_before_the_deadline_once_it_has_shipped(direct_vm, pot, stubs):
    pledge(direct_vm, pot)
    stubs.shipped_in_time()
    set_date(direct_vm, BEFORE)
    pot.claim(GOAL_ID)
    assert stubs.transfers[0]["to"] == PAYEE


def test_nothing_is_claimed_without_a_release_seen_in_time(direct_vm, pot, stubs):
    pledge(direct_vm, pot)
    with direct_vm.expect_revert("not been seen in time"):
        pot.claim(GOAL_ID)
    assert stubs.transfers == []


def test_a_pot_is_claimed_once(direct_vm, pot, stubs):
    pledge(direct_vm, pot)
    stubs.shipped_in_time()
    pot.claim(GOAL_ID)
    with direct_vm.expect_revert("already claimed"):
        pot.claim(GOAL_ID)
    assert len(stubs.transfers) == 1


def test_anyone_may_claim_because_the_payee_is_fixed(direct_vm, pot, stubs):
    pledge(direct_vm, pot)
    stubs.shipped_in_time()
    with direct_vm.prank(STRANGER):
        pot.claim(GOAL_ID)
    assert stubs.transfers[0]["to"] == PAYEE


def test_a_status_about_another_goal_cannot_pay_this_one(direct_vm, pot, stubs):
    pledge(direct_vm, pot)
    stubs.shipped_in_time()
    stubs.state["goal_id"] = "0x00:other"
    with direct_vm.expect_revert("different goal"):
        pot.claim(GOAL_ID)


# --------------------------------------------------------------------
# refunding
# --------------------------------------------------------------------


def test_after_a_missed_deadline_each_backer_takes_back_exactly_their_own(direct_vm, pot, stubs):
    pledge(direct_vm, pot, who=BACKER, amount=PLEDGE)
    pledge(direct_vm, pot, who=OTHER, amount=PLEDGE * 3)
    set_date(direct_vm, AFTER)
    with direct_vm.prank(BACKER):
        pot.refund(GOAL_ID)
    with direct_vm.prank(OTHER):
        pot.refund(GOAL_ID)
    assert stubs.transfers == [
        {"to": BACKER, "value": PLEDGE, "kind": EVM_PAY},
        {"to": OTHER, "value": PLEDGE * 3, "kind": EVM_PAY},
    ]
    assert pot.reserves()["committed"] == "0"


def test_no_refund_before_the_deadline(direct_vm, pot, stubs):
    """Pledges are commitments: a maintainer must be able to count the pot."""
    pledge(direct_vm, pot)
    with direct_vm.prank(BACKER):
        with direct_vm.expect_revert("not passed yet"):
            pot.refund(GOAL_ID)
    assert stubs.transfers == []


def test_no_refund_when_the_release_was_seen_in_time(direct_vm, pot, stubs):
    pledge(direct_vm, pot)
    stubs.shipped_in_time()
    set_date(direct_vm, AFTER)
    with direct_vm.prank(BACKER):
        with direct_vm.expect_revert("belongs to the payee"):
            pot.refund(GOAL_ID)


def test_a_version_out_without_the_payee_opens_refunds_at_once(direct_vm, pot, stubs):
    """It can never pay, so there is nothing to wait for."""
    pledge(direct_vm, pot)
    stubs.came_out_unclaimed()
    set_date(direct_vm, BEFORE)
    with direct_vm.prank(BACKER):
        pot.refund(GOAL_ID)
    assert stubs.transfers == [{"to": BACKER, "value": PLEDGE, "kind": EVM_PAY}]
    with direct_vm.expect_revert("not been seen in time"):
        pot.claim(GOAL_ID)


def test_a_backer_refunds_once(direct_vm, pot, stubs):
    pledge(direct_vm, pot)
    set_date(direct_vm, AFTER)
    with direct_vm.prank(BACKER):
        pot.refund(GOAL_ID)
        with direct_vm.expect_revert("nothing pledged"):
            pot.refund(GOAL_ID)
    assert len(stubs.transfers) == 1


def test_nobody_refunds_what_they_did_not_pledge(direct_vm, pot, stubs):
    pledge(direct_vm, pot)
    set_date(direct_vm, AFTER)
    with direct_vm.prank(STRANGER):
        with direct_vm.expect_revert("nothing pledged"):
            pot.refund(GOAL_ID)
    assert stubs.transfers == []


def test_claim_and_refund_are_never_both_open(direct_vm, pot, stubs):
    """Shipped in time: only claim. Not shipped: only refund, and only late."""
    pledge(direct_vm, pot)
    set_date(direct_vm, AFTER)
    with direct_vm.expect_revert("not been seen in time"):
        pot.claim(GOAL_ID)
    with direct_vm.prank(BACKER):
        pot.refund(GOAL_ID)
    assert [t["to"] for t in stubs.transfers] == [BACKER]


# --------------------------------------------------------------------
# reading
# --------------------------------------------------------------------


def test_the_pot_reads_only_what_it_was_deployed_with(direct_vm, pot):
    got = pot.settings()
    assert got["goal"].lower() == GOAL_AT
    assert got["watch"].lower() == WATCH_AT


def test_a_goal_nobody_backed_says_so(direct_vm, pot):
    with direct_vm.expect_revert("nobody has pledged"):
        pot.get_fund(GOAL_ID)
