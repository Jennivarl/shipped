# SHIPPED

Fund the release you are waiting for. The maintainer is paid only when the public registry shows it.

Open-source maintainers are asked for features constantly and paid for them rarely. The crowdfunding that does exist pays on a promise: backers send money, and then hope. SHIPPED pays on proof. Anyone posts a goal for an exact version of a package, backers pledge toward it, and GenLayer validators read the registry itself. If that version appears before the deadline, naming the maintainer, the pot is theirs. If it does not, every backer takes back exactly what they put in.

**Live site:** [shipped-ten.vercel.app](https://shipped-ten.vercel.app/) — connect any browser wallet. A wallet new to Studio Next is topped up once with test GEN from the network's faucet, so a visitor can take part straight away.

| contract | what it does |
|---|---|
| **GOAL** | The release being paid for: registry, package, exact version, payee, deadline. Fixed when posted. |
| **WATCH** | Reads the version's own document from PyPI or npm under consensus. Records the moment it was first seen. |
| **POT** | Many backers' pledges. Pays the payee on a release seen in time; refunds each backer after a deadline missed. |
| **BADGE** | The reference consumer: endorsements that only open for a release that counted. |

| | |
|---|---|
| Network | GenLayer Studio Next, chain id 61997, `https://studio-next.genlayer.com/api` |
| Engine | Consensus v0.6, GenVM v0.3, runner `py-genlayer:5jycge...` |
| GOAL | [`0x792EA02B091490ECEF03E9F8e8fce36fE6c39b8f`](https://explorer-studio-dev.genlayer.com/address/0x792EA02B091490ECEF03E9F8e8fce36fE6c39b8f) |
| WATCH | [`0x0e01943Bf3b3e748867285975dAD3FfD55B0b57a`](https://explorer-studio-dev.genlayer.com/address/0x0e01943Bf3b3e748867285975dAD3FfD55B0b57a) |
| POT | [`0xD40ADbCf88c6E39b177227A96cb64771FF398e84`](https://explorer-studio-dev.genlayer.com/address/0xD40ADbCf88c6E39b177227A96cb64771FF398e84) |
| BADGE | [`0xFD88eccdd3B9Acd13E04436074D665BCd3229C21`](https://explorer-studio-dev.genlayer.com/address/0xFD88eccdd3B9Acd13E04436074D665BCd3229C21) |
| Tests | 159, `python -m pytest -q` |

---

## The proof is one HTTP status

Both registries serve a version's own document at a fixed URL and answer 404 for a version that was never published:

```
https://pypi.org/pypi/<package>/<version>/json
https://registry.npmjs.org/<package>/<version>
```

So "was 2.0.0 published?" is a status code plus the document naming the version back. There is no parsing of release notes, no model, and no judgement for anyone to argue with. Every validator fetches the same URL, built by the contract from the goal's terms, and agrees with the leader only if they reached the same verdict for the same reason.

## Nobody can collect on somebody else's release

Anyone can post a goal. So anyone could post one for the next version of a popular package, name **themselves** as the payee, gather pledges, and wait for the real team to ship.

SHIPPED closes that with the release itself. **A version only counts if its own published metadata contains the payee's address**: in the README on PyPI, or in a field such as `funding` in `package.json` on npm. Both registries make a published version immutable, so only someone with the right to publish that package can direct the money, and only by publishing. A release that exists but does not name the payee closes the goal: it can never pay, so no new pledge is taken and every backer can take their money back at once.

## Only a release made after the goal can be funded

A steward found the second way to collect on work already done. A maintainer could publish a version naming themselves, then post a goal for it, gather pledges, and claim the moment anyone checked.

So **no pledge is taken until the network has confirmed the version is not out yet.** The first `not_yet` reading is recorded as the moment the version was confirmed absent, and POT refuses every pledge before it. A version the network finds already published before that, whoever it names, closes the goal for good as `existed`: it was never a release this goal could have paid for.

| what the network saw | what it means for the goal |
|---|---|
| nothing yet | pledges refused: "check the registry first" |
| first `not_yet` | confirmed absent: pledges open |
| `shipped` after that, in time | the pot is the payee's |
| `unclaimed` after that | closed: no new pledges, refunds open at once |
| `shipped` or `unclaimed` before any `not_yet` | closed as `existed`: never funded, never paid |

## An ambiguous reading counts for nobody

| what the registry said | verdict | what changes |
|---|---|---|
| 200, names the version and the payee | `shipped` | the release is recorded, at this moment, permanently |
| 200, names the version, not the payee | `unclaimed` | the goal closes: a published version can never name the payee later |
| 404 | `not_yet` | the first one opens pledges; later ones change nothing |
| anything else, or no answer | `unknown` | nothing |

This is deliberately different from how a bill should treat an unreachable host (see [METER](https://github.com/Jennivarl/meter), which counts it against the provider). Here, reading an outage as "not shipped" could refund backers for a release that exists, and reading it as "shipped" could pay for one that does not. Either direction moves money wrongly, so neither does. The maintainer, who gains from being seen, can simply check again.

---

## The rules, and what each one stops

**Shipping is proven by the network seeing it, at the moment it saw it.** Not by a date the registry reports, and not by a date anybody types. The maintainer checks the moment the release is out.

**Only an observation before the deadline counts.** Checks after the deadline are refused outright, so a late release can never be recorded as if it were on time.

**Once seen, it is final.** Further checks are refused, so a yanked file, a registry outage or a stale mirror can never take back a payout already earned. The same holds for a closed goal: nothing seen later reopens it.

**No pledge before the network confirms the version is missing.** So a release that already exists cannot be funded after the fact and claimed at once.

**Pledges are commitments.** There is no taking one back before the deadline. A maintainer deciding whether to cut a release must be able to count the pot.

**Package names are stored canonically.** `Typing_Extensions` and `typing-extensions` are one package on PyPI, so they are one goal here, never two pots.

**Every cross-contract address is fixed at deployment.** No caller can point POT at a different watcher, or WATCH at a different set of terms.

## Every pledge has exactly one way out

| what happened | the way out |
|---|---|
| the release was seen in time, naming the payee | `claim` pays the payee the whole pot, once. Anyone can send it |
| the deadline passed without that | each backer calls `refund` and takes back exactly their own pledge |
| the version came out without naming the payee | the same refund, at once, without waiting for the deadline |

They cannot both be open: `claim` needs a release seen in time, `refund` needs the deadline passed or the goal closed without one, and once either happens nothing more can be seen. Refunds are pulled by each backer rather than pushed in a loop, so no call ever has to pay an unbounded list.

---

## What consensus derived, and what was copied

| stored field | where it comes from | derived or copied |
|---|---|---|
| each check's verdict and reason | every validator fetched the registry URL itself and reached the same pair | derived |
| the URL fetched | built by the contract from the goal's registry, package and version | derived |
| the moment a release was seen | the checking transaction's own `datetime` | derived |
| the moment it was confirmed absent | the first `not_yet` check's own `datetime` | derived |
| whether the goal is closed, and why | which verdict consensus reached, and whether absence was confirmed first | derived |
| the deadline | the posting transaction's time plus the hours given | derived |
| the canonical package name | normalised by the contract (PEP 503 on PyPI) | derived |
| registry, package, version, payee | the organiser's goal, immutable | theirs, immutably |
| each pledge | the backer's own transfer | theirs |

## What a dishonest leader can try

| the lie | what it would buy | what happens | test |
|---|---|---|---|
| claim a release that is not there | the pot, for nothing | rejected | `test_a_validator_rejects_a_leader_claiming_a_release_that_is_not_there` |
| hide a release that is there | refunds for a release that happened | rejected | `test_a_validator_rejects_a_leader_hiding_a_release_that_is_there` |
| skip the payee check | a stranger paid for the real team's work | rejected | `test_a_validator_rejects_a_leader_who_ignores_the_payee_check` |
| agree on the verdict, change the reason | a misleading record | rejected: the reason is compared too | `test_validators_must_agree_on_the_reason_too` |
| crash instead of answering | stalls the check | rejected | `test_a_validator_rejects_a_leader_that_errored` |

---

## Verified live on Studio Next

Run against the real PyPI registry from a second wallet, on the contracts in this repo. Every address in [`deploy/live.json`](deploy/live.json) runs the exact bundle committed here, which `deploy/verify.mjs` proves by hashing the source carried in each deploy transaction.

**A release that is already out.** A goal on `requests 2.31.0`, published long ago, naming the posting wallet as payee. It must never take a pledge or pay.

| step | transaction | result |
|---|---|---|
| Post the goal | [`0xabc66cd7...`](https://explorer-studio-dev.genlayer.com/tx/0xabc66cd73e6d623ee65ad77acca026845a48c7a8baab1dfa9efb13bb19c26191) | `requests` `2.31.0`, payee `0xa4Df…e4a0`, one hour |
| Pledge, before any check | [`0xfc8959a0...`](https://explorer-studio-dev.genlayer.com/tx/0xfc8959a0809c4e5aa751ab47c8ab13a791abb6a8e3dc97d48acc5dd8d14e8475) | **refused**: *the network has not confirmed this version is unpublished yet; check the registry first* |
| Check the registry | [`0x1a946258...`](https://explorer-studio-dev.genlayer.com/tx/0x1a9462587fc0d61147301982a7f8ec380bf29f80629cfc625cbd0d5d683a6f14) | PyPI answered 200 for the version: the goal closes as **`existed`**, never confirmed absent |
| Pledge again | [`0xbddfd310...`](https://explorer-studio-dev.genlayer.com/tx/0xbddfd310d8624c67c57978996edbb3844ba186f59c371dca50d6dcf83a600c28) | **refused**: *that version was already out before the network confirmed it absent, so it cannot be funded* |
| Claim | [`0x9fbba503...`](https://explorer-studio-dev.genlayer.com/tx/0x9fbba5033fa7492895f77f4d884b8e67b6f6c6d09db41e238a40e62a9b3923a2) | **refused**: nothing was ever pledged, and nothing can be |

**A release that is not out yet.** A goal on `requests 99.0.0`, which does not exist.

| step | transaction | result |
|---|---|---|
| Post the goal | [`0xe678fae5...`](https://explorer-studio-dev.genlayer.com/tx/0xe678fae5bc2ee4a8e4baa39426e2ce740658f5f4d48ce5f5d09c54d1a09a0aa3) | one-hour deadline |
| Pledge, before confirmation | [`0x2f1cb6ac...`](https://explorer-studio-dev.genlayer.com/tx/0x2f1cb6aca582344a27288f1c8753d4b9c7213e13af6fe87c42986f76d4971d6f) | **refused**: *check the registry first* |
| Check the registry | [`0xaacd90ba...`](https://explorer-studio-dev.genlayer.com/tx/0xaacd90baab2526265aecc18eed13a69e4dc43b4a514fd9906c368e4e0ff9368c) | PyPI answered 404: **`not_yet`**, recorded as the moment the version was confirmed absent |
| Pledge | [`0xac221d9f...`](https://explorer-studio-dev.genlayer.com/tx/0xac221d9f66b9c545c00733a20d06590f31e72c0f7b48a9237a4ea4e3894b30ca) | 0.02 GEN, accepted |
| Refund, too early | [`0xb908282d...`](https://explorer-studio-dev.genlayer.com/tx/0xb908282d4d2e5ca91f63e4d8f338d012c2d31b3714fa9afc0ee42274e6fcf5e4) | **refused**: *the deadline has not passed yet* |
| Endorse on BADGE | [`0x157907ea...`](https://explorer-studio-dev.genlayer.com/tx/0x157907ea4fde52a64156ef8181b027926062ac7a47f21dfcc4c8bdb2f96fa0c5) | **refused**: *that release has not been seen in time, so this stays shut* |
| Check, after the deadline | [`0xdc410e52...`](https://explorer-studio-dev.genlayer.com/tx/0xdc410e52317f1947820eb4b21da80fdeb95d466f279e5008042af1f13bebb596) | **refused**: *the deadline has passed, so nothing seen now could count* |
| Claim, after the deadline | [`0x51c64a64...`](https://explorer-studio-dev.genlayer.com/tx/0x51c64a64328d06d45f04971c5bead08e393a345280dd1c9c2e86eaf3b503c773) | **refused**: *the release has not been seen in time* |
| Refund | [`0xe4295112...`](https://explorer-studio-dev.genlayer.com/tx/0xe42951121a4351230fa26d5e358c824811f953d22b97d4ff43e4ba69b1abd758) | the pledge back to the backer: the fund's total and POT `committed` both back to `0` |

**Not shown live:** a paid release, and a version that comes out without the payee after being confirmed absent. Both need a real package version published during the run, which this run did not do. Both are covered by the test suite (`test_a_release_seen_in_time_pays_the_payee_everything`, `test_a_version_out_without_the_payee_is_final`, `test_a_version_out_without_the_payee_opens_refunds_at_once`), and the registry check behind them is the same one that produced the results above.

**Through the site.** The same lifecycle driven through [shipped-ten.vercel.app](https://shipped-ten.vercel.app/) in a real browser, with a wallet that signs every transaction. The site's own code builds, sends and follows each one to its verdict, and it asks for the registry check before it shows the pledge box.

| step | transaction | result |
|---|---|---|
| Post the goal | [`0x9c18cf40...`](https://explorer-studio-dev.genlayer.com/tx/0x9c18cf40741d397b95c9ec819ca9421a0ba14567ca06faee50492ab812bf720a) | `requests` `99.2.0`, one hour |
| Check the registry | [`0xf4dcf595...`](https://explorer-studio-dev.genlayer.com/tx/0xf4dcf595c98fe51bab78d40b2cd8b1f7ebe81538f524eef6795d8c7f6ee0fda5) | PyPI answered 404: **`not_yet`**, so pledges open |
| Pledge | [`0x8ea159ae...`](https://explorer-studio-dev.genlayer.com/tx/0x8ea159aef50db2cf9ba8000e84ab09fdcfcb545f734a8be342db661ca7d6df0d) | 0.01 GEN |
| Refund my pledge, after the deadline | [`0x99a2001a...`](https://explorer-studio-dev.genlayer.com/tx/0x99a2001a38e087f23dafaa0c307675d0b1faf32562fd11ada3913d6671815b55) | the pledge back to the backer |

---

## Limits, stated plainly

- **The maintainer has to put the payee address in the release.** That is the price of nobody being able to impersonate them. It is one line in a README or in `package.json`, and it has to be there before publishing, because a published version cannot be edited.
- **Somebody has to check before the deadline.** A release published at 23:59 and first checked at 00:01 does not count. The maintainer is the one with the incentive, and the site puts the button on every goal.
- **It proves a version was published, not that it is good.** SHIPPED pays for the release named in the goal. Whether that release does what backers hoped is outside what a registry can say.
- **Two registries.** PyPI and npm, because both serve an immutable per-version document at a fixed URL that answers 404 when absent. Others can be added on the same terms.

---

## Running it

```sh
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
python -m deploy.build_bundle          # the four files that actually deploy
python -m pytest -q                    # 159 tests, no chain and no network
```

```sh
npm install
export GENLAYER_KEYSTORE=~/.genlayer/keystores/mykey.json
export GENLAYER_PASSWORD=...
node deploy/deploy.mjs contracts/goal_bundle.py
node deploy/deploy.mjs contracts/watch_bundle.py <goal address>
node deploy/deploy.mjs contracts/pot_bundle.py   <goal address> <watch address>
node deploy/deploy.mjs contracts/badge_bundle.py <watch address> <goal id>
node deploy/verify.mjs                 # no key needed: each live contract runs this exact bundle
```

The site is in [`site/`](site/): React, Vite and Tailwind, deployed on Vercel. It reads the contracts straight from the browser and signs with the visitor's own wallet; every payout it sends reserves the funded message allocation the payment needs. It polls slowly and pauses in background tabs, because Studio Next allows each visitor 30 requests a minute and 500 an hour.

```sh
cd site && npm install && npm run dev
```

## Layout

```
contracts/releases.py       the pure part: names, versions, the URL, what an answer proves
contracts/goal.py           the release being paid for
contracts/watch.py          reads the registry under consensus
contracts/pot.py            pledges, payout and refunds
contracts/badge.py          reference consumer: endorsements gated on a release that counted
contracts/*_bundle.py       what actually deploys. Generated, never edited
deploy/                     build, deploy and verify
site/                       the web app
test/                       159 tests
```

## License

MIT
