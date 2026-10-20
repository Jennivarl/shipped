"""
BADGE run for real in direct mode, against a stand-in WATCH.

The reference consumer. It must refuse a release that has not been seen,
and must use `in_time` rather than `shipped`.
"""

import sys
from pathlib import Path

import pytest

from test.stubs import AFTER, GOAL_ID, STRANGER, WATCH_AT, Stubs

BUNDLE = str(Path(__file__).resolve().parent.parent / "contracts" / "badge_bundle.py")

OPERATOR = b"\xa0" * 20


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
def badge(direct_vm, direct_deploy, stubs):
    with direct_vm.prank(OPERATOR):
        contract = direct_deploy(BUNDLE, watch=WATCH_AT, goal_id=GOAL_ID)
    direct_vm.strict_mocks = False
    set_date(direct_vm, AFTER)
    return contract


def test_a_release_not_yet_seen_keeps_it_shut(direct_vm, badge):
    with direct_vm.expect_revert("not been seen in time"):
        badge.endorse("shipped it")


def test_a_release_seen_but_not_in_time_keeps_it_shut(direct_vm, badge, stubs):
    """`shipped` alone is not the promise; `in_time` is."""
    stubs.state = {**stubs.state, "shipped": True, "in_time": False, "shipped_at": AFTER}
    with direct_vm.expect_revert("not been seen in time"):
        badge.endorse("shipped it")


def test_a_release_seen_in_time_opens_it(direct_vm, badge, stubs):
    stubs.shipped_in_time()
    got = badge.endorse("thank you")
    assert got["endorsed"] is True
    assert badge.history()[0]["note"] == "thank you"


def test_anyone_may_endorse_once_it_counts(direct_vm, badge, stubs):
    stubs.shipped_in_time()
    with direct_vm.prank(STRANGER):
        badge.endorse("thanks")
    assert badge.history()[0]["actor"].lower() == "0x" + STRANGER.hex()


def test_a_status_about_another_goal_cannot_open_it(direct_vm, badge, stubs):
    stubs.shipped_in_time()
    stubs.state["goal_id"] = "0x00:other"
    with direct_vm.expect_revert("different goal"):
        badge.endorse("thanks")


def test_a_badge_must_name_its_goal(direct_vm, direct_deploy, stubs):
    with direct_vm.expect_revert("name the goal"):
        direct_deploy(BUNDLE, watch=WATCH_AT, goal_id="  ")


def test_standing_reports_where_the_goal_has_got_to(direct_vm, badge, stubs):
    assert badge.standing()["open"] is False
    stubs.shipped_in_time()
    got = badge.standing()
    assert got["open"] is True
    assert got["operator"].lower() == "0x" + OPERATOR.hex()
    assert got["watch"].lower() == WATCH_AT


def test_a_long_note_is_trimmed_rather_than_refused(direct_vm, badge, stubs):
    stubs.shipped_in_time()
    badge.endorse("x" * 500)
    assert len(badge.history()[0]["note"]) == 200
