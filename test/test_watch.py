"""
WATCH run for real in direct mode, against a stand-in GOAL and a mocked
registry.

Half of these run the validator side: what matters is not what one leader
read, but whether an honest validator would agree, and whether a leader
claiming a release that is not there would be caught.
"""

import sys
from pathlib import Path

import pytest

from test.stubs import AFTER, BEFORE, GOAL_AT, GOAL_ID, PAYEE_HEX, STRANGER, VERSION, Stubs

BUNDLE = str(Path(__file__).resolve().parent.parent / "contracts" / "watch_bundle.py")

URL = r"pypi\.org/pypi/requests/2\.33\.0/json"


def set_date(vm, stamp):
    vm.warp(stamp)
    message = sys.modules.get("genlayer.message")
    if message is not None and isinstance(getattr(message, "raw", None), dict):
        message.raw["datetime"] = stamp
    gl = sys.modules.get("genlayer.gl")
    if gl is not None and getattr(gl, "message_raw", None) is not None:
        gl.message_raw["datetime"] = stamp


def registry(vm, status=200, body=None):
    vm.clear_mocks()
    if body is None:
        body = '{"info":{"version":"' + VERSION + '","description":"funding ' + PAYEE_HEX + '"}}'
    vm.mock_web(URL, {"status": status, "body": body})


@pytest.fixture
def stubs(direct_vm):
    return Stubs().install(direct_vm)


@pytest.fixture
def watch(direct_vm, direct_deploy, stubs):
    contract = direct_deploy(BUNDLE, goal=GOAL_AT)
    direct_vm.strict_mocks = False
    set_date(direct_vm, BEFORE)
    return contract


EARLY = "2026-10-20T12:00:00Z"
NO_PAYEE = '{"info":{"version":"' + VERSION + '"}}'


def check(vm, watch, when=BEFORE, **serve):
    set_date(vm, when)
    registry(vm, **serve)
    return watch.check(GOAL_ID)


def confirm_absent(vm, watch, when=EARLY):
    """The reading every goal needs before it can take a pledge."""
    return check(vm, watch, when=when, status=404, body="")


def test_a_release_naming_the_payee_before_the_deadline_counts(direct_vm, watch):
    confirm_absent(direct_vm, watch)
    got = check(direct_vm, watch)
    assert got["shipped"] is True
    assert got["in_time"] is True
    assert got["shipped_at"] == BEFORE
    assert got["last_note"] == "the release names this payee"


def test_a_release_that_does_not_name_the_payee_does_not_count(direct_vm, watch):
    confirm_absent(direct_vm, watch)
    got = check(direct_vm, watch, body=NO_PAYEE)
    assert got["shipped"] is False
    assert got["in_time"] is False
    assert got["last_verdict"] == "unclaimed"
    assert got["closed"] == "unclaimed"


def test_the_first_not_yet_is_recorded_as_confirmed_absence(direct_vm, watch):
    got = confirm_absent(direct_vm, watch)
    assert got["absent_at"] == EARLY
    got = confirm_absent(direct_vm, watch, when="2026-10-20T15:00:00Z")
    assert got["absent_at"] == EARLY  # the first confirmation stands


def test_an_outage_does_not_confirm_absence(direct_vm, watch):
    got = check(direct_vm, watch, status=503, body="")
    assert got["absent_at"] == ""


def test_a_release_that_already_existed_closes_the_goal(direct_vm, watch):
    """Found published before anyone confirmed it absent: never payable."""
    got = check(direct_vm, watch)
    assert got["shipped"] is False
    assert got["in_time"] is False
    assert got["closed"] == "existed"


def test_a_release_that_already_existed_can_never_become_payable(direct_vm, watch):
    check(direct_vm, watch)
    with direct_vm.expect_revert("can never pay"):
        confirm_absent(direct_vm, watch, when=BEFORE)
    with direct_vm.expect_revert("can never pay"):
        check(direct_vm, watch)
    assert watch.status(GOAL_ID)["in_time"] is False


def test_an_existing_release_without_the_payee_also_closes_the_goal(direct_vm, watch):
    got = check(direct_vm, watch, body=NO_PAYEE)
    assert got["closed"] == "existed"


def test_a_version_out_without_the_payee_is_final(direct_vm, watch):
    """Published versions cannot be edited, so it can never name the payee."""
    confirm_absent(direct_vm, watch)
    check(direct_vm, watch, body=NO_PAYEE)
    with direct_vm.expect_revert("can never pay"):
        check(direct_vm, watch)
    assert watch.status(GOAL_ID)["in_time"] is False


def test_a_version_not_yet_published_does_not_count(direct_vm, watch):
    got = check(direct_vm, watch, status=404, body="")
    assert got["shipped"] is False
    assert got["last_verdict"] == "not_yet"


def test_a_registry_outage_changes_nothing(direct_vm, watch):
    got = check(direct_vm, watch, status=503, body="")
    assert got["shipped"] is False
    assert got["last_verdict"] == "unknown"
    assert got["checks"] == "1"


def test_an_unreachable_registry_changes_nothing(direct_vm, watch):
    set_date(direct_vm, BEFORE)
    direct_vm.clear_mocks()
    got = watch.check(GOAL_ID)
    assert got["shipped"] is False
    assert got["last_note"] == "the registry could not be reached"


def test_not_yet_then_shipped_is_recorded_at_the_moment_it_was_seen(direct_vm, watch):
    confirm_absent(direct_vm, watch)
    got = check(direct_vm, watch, when=BEFORE)
    assert got["shipped_at"] == BEFORE
    assert got["checks"] == "2"


def test_once_seen_it_is_final(direct_vm, watch):
    """A later outage or a yanked file cannot take back an earned payout."""
    confirm_absent(direct_vm, watch)
    check(direct_vm, watch)
    with direct_vm.expect_revert("already been seen"):
        check(direct_vm, watch, status=404, body="")
    assert watch.status(GOAL_ID)["in_time"] is True


def test_nothing_is_checked_after_the_deadline(direct_vm, watch):
    """A release seen late could never count, so it is not recorded at all."""
    with direct_vm.expect_revert("deadline has passed"):
        check(direct_vm, watch, when=AFTER)


def test_anyone_may_check_because_the_reading_is_the_registrys(direct_vm, watch):
    confirm_absent(direct_vm, watch)
    set_date(direct_vm, BEFORE)
    registry(direct_vm)
    with direct_vm.prank(STRANGER):
        got = watch.check(GOAL_ID)
    assert got["in_time"] is True


def test_the_url_comes_from_the_goal_and_nothing_else(direct_vm, watch, stubs):
    stubs.set_target(url="https://pypi.org/pypi/requests/9.9.9/json")
    got = check(direct_vm, watch)
    # The mock answers only the real URL, so a fetch of anything else fails.
    assert got["last_note"] == "the registry could not be reached"


def test_terms_about_another_goal_are_refused(direct_vm, watch, stubs):
    stubs.set_target(goal_id="0x00:other")
    with direct_vm.expect_revert("different goal"):
        check(direct_vm, watch)


def test_a_goal_never_checked_reports_not_shipped(direct_vm, watch):
    got = watch.status(GOAL_ID)
    assert got["shipped"] is False
    assert got["in_time"] is False
    assert got["checks"] == "0"
    assert got["absent_at"] == ""
    assert got["closed"] == ""


# --------------------------------------------------------------------
# the validator side
# --------------------------------------------------------------------


def leader(verdict, note):
    return {"verdict": verdict, "note": note}


def test_a_validator_agrees_when_it_reads_the_same_registry(direct_vm, watch):
    check(direct_vm, watch)
    assert direct_vm.run_validator() is True


def test_a_validator_rejects_a_leader_claiming_a_release_that_is_not_there(direct_vm, watch):
    """The lie that pays out a pot for nothing."""
    check(direct_vm, watch, status=404, body="")
    assert direct_vm.run_validator(leader_result=leader("shipped", "the release names this payee")) is False


def test_a_validator_rejects_a_leader_hiding_a_release_that_is_there(direct_vm, watch):
    """The lie that refunds backers for a release that happened."""
    check(direct_vm, watch)
    assert direct_vm.run_validator(leader_result=leader("not_yet", "the registry has no such version")) is False


def test_a_validator_rejects_a_leader_who_ignores_the_payee_check(direct_vm, watch):
    check(direct_vm, watch, body='{"info":{"version":"' + VERSION + '"}}')
    assert direct_vm.run_validator(leader_result=leader("shipped", "the release names this payee")) is False


def test_validators_must_agree_on_the_reason_too(direct_vm, watch):
    check(direct_vm, watch, status=503, body="")
    assert direct_vm.run_validator(leader_result=leader("unknown", "the registry answered 500")) is False


def test_a_validator_rejects_a_result_of_the_wrong_shape(direct_vm, watch):
    check(direct_vm, watch)
    assert direct_vm.run_validator(leader_result="shipped") is False


def test_a_validator_rejects_a_leader_that_errored(direct_vm, watch):
    check(direct_vm, watch)
    assert direct_vm.run_validator(leader_error=Exception("boom")) is False
