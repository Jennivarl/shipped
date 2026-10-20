"""
The pure core, tested without a chain, a network or money.

What a registry answer means, which names and versions are allowed, and
the one URL that is ever fetched. The payee check is the one to read
twice: it is what stops a stranger collecting on somebody else's release.
"""

import datetime

import pytest

from contracts.releases import (
    MAX_LEAD,
    MIN_LEAD,
    NOT_YET,
    NPM,
    PYPI,
    SHIPPED,
    UNCLAIMED,
    UNKNOWN,
    classify,
    epoch_seconds,
    names_payee,
    names_version,
    normalise_package,
    registry_url,
    unreached,
    valid_package,
    valid_version,
)

PAYEE = "0x" + "b0" * 20


def doc(version="2.33.0", extra=""):
    return '{"info":{"version":"' + version + '","description":"' + extra + '"}}'


# --------------------------------------------------------------------
# what a registry answer means
# --------------------------------------------------------------------


def test_a_release_naming_its_version_and_payee_has_shipped():
    assert classify(200, doc(extra="funding: " + PAYEE), "2.33.0", PAYEE) == {
        "verdict": SHIPPED,
        "note": "the release names this payee",
    }


def test_the_payee_is_matched_in_either_case():
    assert classify(200, doc(extra=PAYEE.upper().replace("0X", "0x")), "2.33.0", PAYEE)["verdict"] == SHIPPED


def test_a_release_that_does_not_name_the_payee_is_unclaimed():
    """
    The attack this exists for: a stranger posts a goal naming themselves,
    the real team ships, and the release does not name the stranger.
    """
    assert classify(200, doc(extra="no address here"), "2.33.0", PAYEE) == {
        "verdict": UNCLAIMED,
        "note": "the release does not name this payee",
    }


def test_a_release_naming_a_different_address_is_unclaimed():
    other = "0x" + "c0" * 20
    assert classify(200, doc(extra=other), "2.33.0", PAYEE)["verdict"] == UNCLAIMED


def test_a_404_means_not_yet():
    assert classify(404, "", "2.33.0", PAYEE) == {"verdict": NOT_YET, "note": "the registry has no such version"}


def test_a_200_that_is_not_the_registrys_document_proves_nothing():
    """A CDN page or a redirect target that does not name the version."""
    assert classify(200, "<html>hello</html>", "2.33.0", PAYEE)["verdict"] == UNKNOWN


def test_a_200_for_a_different_version_proves_nothing():
    assert classify(200, doc(version="2.32.0", extra=PAYEE), "2.33.0", PAYEE)["verdict"] == UNKNOWN


@pytest.mark.parametrize("status", [301, 403, 429, 500, 503])
def test_any_other_answer_proves_nothing_either_way(status):
    """
    Unlike a bill, an ambiguous reading must not count here: either
    direction could move money wrongly. The maintainer can check again.
    """
    assert classify(status, doc(extra=PAYEE), "2.33.0", PAYEE)["verdict"] == UNKNOWN


def test_an_unreachable_registry_proves_nothing():
    assert unreached()["verdict"] == UNKNOWN


def test_both_json_spacings_name_the_version():
    assert names_version('{"version":"1.0.0"}', "1.0.0")
    assert names_version('{"version": "1.0.0"}', "1.0.0")
    assert not names_version('{"version":"1.0.00"}', "1.0.0")
    assert not names_version('{"version":"11.0.0"}', "1.0.0")


def test_a_version_is_not_found_inside_a_longer_one():
    """1.0.0 must not match a document for 1.0.0rc1."""
    assert not names_version('{"version":"1.0.0rc1"}', "1.0.0")


def test_only_a_full_address_can_be_a_payee():
    assert names_payee("x " + PAYEE + " y", PAYEE)
    assert not names_payee(PAYEE, "0x1234")
    assert not names_payee(PAYEE, "")


# --------------------------------------------------------------------
# names, versions and the URL
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "spelling",
    ["Foo_Bar", "foo-bar", "FOO.BAR", "foo__bar", "foo-_.bar"],
)
def test_every_pypi_spelling_of_one_package_is_one_package(spelling):
    assert normalise_package(PYPI, spelling) == "foo-bar"


def test_npm_names_keep_their_scope():
    assert normalise_package(NPM, "@types/node") == "@types/node"


@pytest.mark.parametrize("name", ["requests", "Flask", "zope.interface", "a1", "typing_extensions"])
def test_real_pypi_names_are_accepted(name):
    assert valid_package(PYPI, name)


@pytest.mark.parametrize("name", ["", "-lead", "trail-", "a/b", "../x", "a b", "naïve", "x" * 101])
def test_pypi_names_that_could_leave_the_path_are_refused(name):
    assert not valid_package(PYPI, name)


@pytest.mark.parametrize("name", ["left-pad", "@types/node", "lodash.merge", "a~b"])
def test_real_npm_names_are_accepted(name):
    assert valid_package(NPM, name)


@pytest.mark.parametrize("name", ["Left-Pad", "@types", "@/node", "a/b", "@a/b/c", ".hidden", "_x", "a b"])
def test_npm_names_the_registry_would_refuse_are_refused(name):
    assert not valid_package(NPM, name)


def test_an_unknown_registry_accepts_nothing():
    assert not valid_package("crates", "serde")


@pytest.mark.parametrize("version", ["2.0.0", "1.4", "3", "1.2.3.4", "3.0.0-rc.1", "2.0.0rc1", "1.0.0-beta"])
def test_canonical_versions_are_accepted(version):
    assert valid_version(version)


@pytest.mark.parametrize(
    "version",
    ["", "v2.0.0", "2.0.0.", "2..0", "1.2.3.4.5", "2.0.0-", "2.0.0/../x", "2.0 .0", "latest", "2.0.0-rc."],
)
def test_loose_or_dangerous_versions_are_refused(version):
    assert not valid_version(version)


def test_the_pypi_url_is_the_versions_own_json_document():
    assert registry_url(PYPI, "Requests", "2.33.0") == "https://pypi.org/pypi/requests/2.33.0/json"


def test_the_npm_url_is_the_versions_own_document():
    assert registry_url(NPM, "@types/node", "20.0.0") == "https://registry.npmjs.org/@types/node/20.0.0"


def test_an_unknown_registry_has_no_url():
    with pytest.raises(ValueError):
        registry_url("crates", "serde", "1.0.0")


def test_a_deadline_is_an_hour_to_a_year_away():
    assert MIN_LEAD == 3600
    assert MAX_LEAD == 366 * 24 * 3600


# --------------------------------------------------------------------
# the clock
# --------------------------------------------------------------------


def test_fractional_seconds_do_not_change_the_instant():
    assert epoch_seconds("2026-10-20T09:00:00Z") == epoch_seconds("2026-10-20T09:00:00.5+00:00")


def test_the_clock_agrees_with_the_standard_library_across_a_leap_day():
    day = datetime.date(2024, 2, 29) - datetime.timedelta(days=800)
    for _ in range(1600):
        expected = int(datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.timezone.utc).timestamp())
        assert epoch_seconds(day.isoformat() + "T00:00:00Z") == expected
        day += datetime.timedelta(days=1)
