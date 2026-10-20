"""
The pure part of SHIPPED. No chain, no network, no money.

A crowdfunded bounty on a release: backers pledge toward "version X of
package Y, published by date Z", and the maintainer is paid the pot only if
the public registry shows it. Nothing in this module trusts anybody. It
decides, deterministically, what a registry answer means:

    which registries count             PyPI and npm
    what a package and version may be   the registry's own canonical forms
    the one URL that is ever fetched    built here from those parts
    what the answer proves              published, not yet, or nothing

The proof is deliberately narrow. Both registries serve a version's own
document at a fixed URL, and answer 404 for a version that does not exist.
So the question "was 2.0.0 published?" reduces to one HTTP status plus the
document naming the version back. There is no parsing of release notes,
no model, and no judgement for anybody to argue with.

And the same document settles who is paid. Anyone can post a goal, so
anyone could name themselves as the maintainer of a popular package and
wait for the real team to publish. So the released version must carry the
payee's address in its own published metadata: the README on PyPI, any
field such as `funding` on npm. Both registries make a published version
immutable, so only someone with the right to publish that package can
direct the money, and only by publishing.

Anything else the registry says, a 500, a rate limit, a timeout, proves
nothing in either direction and changes nothing. Here, unlike a bill, an
ambiguous reading must not count: treating it as "not shipped" could
refund backers for a release that exists, and treating it as "shipped"
could pay for one that does not. The maintainer, who gains from a release
being seen, can simply check again.
"""

PYPI = "pypi"
NPM = "npm"
REGISTRIES = (PYPI, NPM)

SHIPPED = "shipped"
UNCLAIMED = "unclaimed"
NOT_YET = "not_yet"
UNKNOWN = "unknown"

VERDICTS = (SHIPPED, UNCLAIMED, NOT_YET, UNKNOWN)

# How far ahead a goal's deadline may be set. Long enough for a real
# release cycle, short enough that pledges are not locked up for years.
MIN_LEAD = 3600
MAX_LEAD = 366 * 24 * 3600

_MAX_NAME = 100


def normalise_package(registry: str, name: str) -> str:
    """
    A package name as the registry identifies it, so two spellings of the
    same package can never become two different goals.

    PyPI follows PEP 503: case-insensitive, and runs of `-`, `_` and `.`
    are the same character. npm names are already lowercase, and a scoped
    name keeps its `@scope/` prefix.
    """
    n = (name or "").strip()
    if registry == PYPI:
        out = []
        for ch in n.lower():
            if ch in "-_.":
                if not out or out[-1] != "-":
                    out.append("-")
            else:
                out.append(ch)
        return "".join(out)
    return n.lower()


def valid_package(registry: str, name: str) -> bool:
    """
    A name the registry itself would accept.

    PyPI: letters, digits, `-`, `_`, `.`, starting and ending alphanumeric.
    npm: lowercase letters, digits, `-`, `.`, `_`, `~`, optionally under one
    `@scope/`. Nothing that could leave the URL path, ever.
    """
    n = (name or "").strip()
    if not n or len(n) > _MAX_NAME:
        return False
    if registry == PYPI:
        if not (n[0].isalnum() and n[-1].isalnum() and n.isascii()):
            return False
        return all(ch.isalnum() or ch in "-_." for ch in n)
    if registry == NPM:
        if n != n.lower() or not n.isascii():
            return False
        body = n
        if n.startswith("@"):
            if n.count("/") != 1:
                return False
            scope, body = n[1:].split("/")
            if not scope or not _npm_part(scope):
                return False
        elif "/" in n:
            return False
        return bool(body) and _npm_part(body) and body[0] not in "._"
    return False


def _npm_part(part: str) -> bool:
    return all(("a" <= ch <= "z") or ("0" <= ch <= "9") or ch in "-._~" for ch in part)


def valid_version(version: str) -> bool:
    """
    A release version in the strict form both registries serve at a fixed
    URL: dot-separated numbers, then optionally one pre-release tag of
    letters and digits joined by `-`, `.` or nothing, like `2.0.0`,
    `1.4`, `3.0.0-rc.1` or `2.0.0rc1`.

    Strict on purpose. A loose version is one the registry might normalise
    to something else, and then the URL asks about a different release.
    """
    v = (version or "").strip()
    if not v or len(v) > 40 or not v.isascii():
        return False
    i = 0
    groups = 0
    while True:
        start = i
        while i < len(v) and v[i].isdigit():
            i += 1
        if i == start:
            return False
        groups += 1
        if i < len(v) and v[i] == "." and i + 1 < len(v) and v[i + 1].isdigit():
            i += 1
            continue
        break
    if groups < 1 or groups > 4:
        return False
    tail = v[i:]
    if not tail:
        return True
    if tail[0] in "-.":
        tail = tail[1:]
    if not tail or not tail[0].isalpha():
        return False
    return all(ch.isalnum() or ch in "-." for ch in tail) and not tail.endswith((".", "-"))


def registry_url(registry: str, package: str, version: str) -> str:
    """
    The one document whose existence is the proof, built here only.

    PyPI serves `/pypi/<name>/<version>/json`; npm serves `/<name>/<version>`.
    Both answer 404 for a version that was never published.
    """
    name = normalise_package(registry, package)
    v = version.strip()
    if registry == PYPI:
        return "https://pypi.org/pypi/" + name + "/" + v + "/json"
    if registry == NPM:
        return "https://registry.npmjs.org/" + name + "/" + v
    raise ValueError("unknown registry")


def names_version(body: str, version: str) -> bool:
    """
    Whether the document names the version back, in either JSON spacing.

    A 200 alone could be a CDN page or a redirect target. The registry's
    own document for a release says which release it is.
    """
    v = version.strip()
    text = body or ""
    return ('"version":"' + v + '"') in text or ('"version": "' + v + '"') in text


def names_payee(body: str, payee: str) -> bool:
    """
    Whether the released version's own metadata carries the payee address.

    Compared case-insensitively, because an address is the same address in
    either case and a README may write it either way.
    """
    address = (payee or "").strip().lower()
    if len(address) != 42 or not address.startswith("0x"):
        return False
    return address in (body or "").lower()


def classify(status: int, body: str, version: str, payee: str) -> dict:
    """
    One registry answer reduced to a verdict and the reason for it.

        200 naming the version and the payee   shipped
        200 naming the version, not the payee  unclaimed: released, but not
                                               by anyone who named this payee
        200 not naming the version             unknown: something answered,
                                               not the registry's document
        404                                    not yet
        anything else                          unknown: proves nothing
    """
    code = int(status)
    if code == 200:
        if not names_version(body, version):
            return {"verdict": UNKNOWN, "note": "a 200 that did not name this version"}
        if names_payee(body, payee):
            return {"verdict": SHIPPED, "note": "the release names this payee"}
        return {"verdict": UNCLAIMED, "note": "the release does not name this payee"}
    if code == 404:
        return {"verdict": NOT_YET, "note": "the registry has no such version"}
    return {"verdict": UNKNOWN, "note": "the registry answered " + str(code)}


def unreached() -> dict:
    return {"verdict": UNKNOWN, "note": "the registry could not be reached"}


def epoch_seconds(stamp: str):
    """
    An ISO-8601 UTC timestamp as whole seconds, or None.

    Only the fixed "YYYY-MM-DDTHH:MM:SS" prefix is read, so the network's
    fractional seconds and a test's whole ones mean the same instant.
    """
    s = (stamp or "").strip()
    if len(s) < 19 or s[4] != "-" or s[7] != "-" or s[10] != "T" or s[13] != ":" or s[16] != ":":
        return None
    for i in (0, 1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18):
        if not ("0" <= s[i] <= "9"):
            return None
    year, month, day = int(s[0:4]), int(s[5:7]), int(s[8:10])
    hour, minute, second = int(s[11:13]), int(s[14:16]), int(s[17:19])
    if not (1 <= month <= 12) or day < 1 or day > _days_in_month(year, month):
        return None
    if hour > 23 or minute > 59 or second > 60:
        return None
    return _days_from_civil(year, month, day) * 86400 + hour * 3600 + minute * 60 + second


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    return 30 if month in (4, 6, 9, 11) else 31


def _days_from_civil(year: int, month: int, day: int) -> int:
    """Integer only and no library, because every validator must agree."""
    y = year - (1 if month <= 2 else 0)
    era = (y if y >= 0 else y - 399) // 400
    year_of_era = y - era * 400
    day_of_year = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return era * 146097 + day_of_era - 719468
