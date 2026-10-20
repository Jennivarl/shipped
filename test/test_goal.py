"""
GOAL run for real in direct mode.

A goal binds nobody and pays nobody, so these are about what it fixes: the
package in canonical form, the exact version, the payee, and a deadline
nobody typed.
"""

import sys
from pathlib import Path

import pytest

from contracts.releases import epoch_seconds

BUNDLE = str(Path(__file__).resolve().parent.parent / "contracts" / "goal_bundle.py")

ORGANISER = b"\xa0" * 20
PAYEE = "0x" + "b0" * 20
NAME = "v2"
GOAL_ID = "0x" + ORGANISER.hex() + ":" + NAME
T0 = "2026-10-20T09:00:00Z"


def set_date(vm, stamp):
    vm.warp(stamp)
    message = sys.modules.get("genlayer.message")
    if message is not None and isinstance(getattr(message, "raw", None), dict):
        message.raw["datetime"] = stamp
    gl = sys.modules.get("genlayer.gl")
    if gl is not None and getattr(gl, "message_raw", None) is not None:
        gl.message_raw["datetime"] = stamp


@pytest.fixture
def book(direct_vm, direct_deploy):
    contract = direct_deploy(BUNDLE)
    direct_vm.strict_mocks = False
    set_date(direct_vm, T0)
    return contract


def post(vm, book, name=NAME, registry="pypi", package="requests", version="2.33.0", payee=PAYEE, hours=48):
    with vm.prank(ORGANISER):
        return book.post(name, registry, package, version, payee, hours)


def test_a_goal_fixes_package_version_payee_and_url(direct_vm, book):
    got = post(direct_vm, book)
    assert got["goal_id"] == GOAL_ID
    assert got["package"] == "requests"
    assert got["version"] == "2.33.0"
    assert got["payee"].lower() == PAYEE
    assert got["url"] == "https://pypi.org/pypi/requests/2.33.0/json"


def test_the_deadline_is_the_posting_time_plus_the_hours(direct_vm, book):
    got = post(direct_vm, book, hours=48)
    assert got["deadline"] == str(epoch_seconds(T0) + 48 * 3600)


def test_the_package_is_stored_in_canonical_form(direct_vm, book):
    got = post(direct_vm, book, package="Typing_Extensions")
    assert got["package"] == "typing-extensions"
    assert got["url"] == "https://pypi.org/pypi/typing-extensions/2.33.0/json"


def test_an_npm_goal_reads_the_npm_registry(direct_vm, book):
    got = post(direct_vm, book, registry="npm", package="@types/node", version="20.0.0")
    assert got["url"] == "https://registry.npmjs.org/@types/node/20.0.0"


def test_a_goal_cannot_be_changed_once_posted(direct_vm, book):
    post(direct_vm, book)
    with direct_vm.expect_revert("cannot be changed"):
        post(direct_vm, book, version="2.34.0")


def test_only_pypi_and_npm_are_registries(direct_vm, book):
    with direct_vm.expect_revert("pypi or npm"):
        post(direct_vm, book, registry="crates")


def test_a_package_name_the_registry_would_refuse_is_refused(direct_vm, book):
    with direct_vm.expect_revert("not a package name"):
        post(direct_vm, book, package="../etc")


def test_a_loose_version_is_refused(direct_vm, book):
    with direct_vm.expect_revert("exactly as the registry lists it"):
        post(direct_vm, book, version="v2.33")


def test_the_zero_address_is_not_a_payee(direct_vm, book):
    with direct_vm.expect_revert("real payee"):
        post(direct_vm, book, payee="0x" + "00" * 20)


@pytest.mark.parametrize("hours", [0, 9000])
def test_a_deadline_must_be_an_hour_to_a_year_away(direct_vm, book, hours):
    with direct_vm.expect_revert("a deadline is"):
        post(direct_vm, book, hours=hours)


def test_a_name_is_letters_digits_hyphen_or_underscore(direct_vm, book):
    with direct_vm.expect_revert("letters, digits"):
        post(direct_vm, book, name="v 2")


def test_asking_for_a_goal_that_does_not_exist_says_so(direct_vm, book):
    with direct_vm.expect_revert("no such goal"):
        book.get("0x00:nothing")


def test_the_list_holds_every_goal(direct_vm, book):
    post(direct_vm, book)
    assert book.goal_list() == [GOAL_ID]
