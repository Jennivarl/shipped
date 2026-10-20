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
| GOAL | [`0x11CE3247F16569C42031F6FE3Dedf07027C1088e`](https://explorer-studio-dev.genlayer.com/address/0x11CE3247F16569C42031F6FE3Dedf07027C1088e) |
| WATCH | [`0xeaAC1bC201E35fB2eF7995fA5B96FA5B425D0B74`](https://explorer-studio-dev.genlayer.com/address/0xeaAC1bC201E35fB2eF7995fA5B96FA5B425D0B74) |
| POT | [`0x5aA0C16F41Ba65952c76Bb27302849F3EA0FC4a4`](https://explorer-studio-dev.genlayer.com/address/0x5aA0C16F41Ba65952c76Bb27302849F3EA0FC4a4) |
| BADGE | [`0xA8Dda8BE699b9775F31AF8700DD5e744db1f35A8`](https://explorer-studio-dev.genlayer.com/address/0xA8Dda8BE699b9775F31AF8700DD5e744db1f35A8) |
| Tests | 148, `python -m pytest -q` |

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

SHIPPED closes that with the release itself. **A version only counts if its own published metadata contains the payee's address**: in the README on PyPI, or in a field such as `funding` in `package.json` on npm. Both registries make a published version immutable, so only someone with the right to publish that package can direct the money, and only by publishing. A release that exists but does not name the payee is recorded as `unclaimed`, and the pot is refunded at the deadline.

## An ambiguous reading counts for nobody

| what the registry said | verdict | what changes |
|---|---|---|
| 200, names the version and the payee | `shipped` | the release is recorded, at this moment, permanently |
| 200, names the version, not the payee | `unclaimed` | nothing |
| 404 | `not_yet` | nothing |
| anything else, or no answer | `unknown` | nothing |

This is deliberately different from how a bill should treat an unreachable host (see [METER](https://github.com/Jennivarl/meter), which counts it against the provider). Here, reading an outage as "not shipped" could refund backers for a release that exists, and reading it as "shipped" could pay for one that does not. Either direction moves money wrongly, so neither does. The maintainer, who gains from being seen, can simply check again.

---

## The rules, and what each one stops

**Shipping is proven by the network seeing it, at the moment it saw it.** Not by a date the registry reports, and not by a date anybody types. The maintainer checks the moment the release is out.

**Only an observation before the deadline counts.** Checks after the deadline are refused outright, so a late release can never be recorded as if it were on time.

**Once seen, it is final.** Further checks are refused, so a yanked file, a registry outage or a stale mirror can never take back a payout already earned.

**Pledges are commitments.** There is no taking one back before the deadline. A maintainer deciding whether to cut a release must be able to count the pot.

**Package names are stored canonically.** `Typing_Extensions` and `typing-extensions` are one package on PyPI, so they are one goal here, never two pots.

**Every cross-contract address is fixed at deployment.** No caller can point POT at a different watcher, or WATCH at a different set of terms.

## Every pledge has exactly one way out

| what happened | the way out |
|---|---|
| the release was seen in time, naming the payee | `claim` pays the payee the whole pot, once. Anyone can send it |
| the deadline passed without that | each backer calls `refund` and takes back exactly their own pledge |

They cannot both be open: `claim` needs a release seen in time, `refund` needs the deadline passed without one, and after the deadline nothing can be seen any more. Refunds are pulled by each backer rather than pushed in a loop, so no call ever has to pay an unbounded list.

---

## What consensus derived, and what was copied

| stored field | where it comes from | derived or copied |
|---|---|---|
| each check's verdict and reason | every validator fetched the registry URL itself and reached the same pair | derived |
| the URL fetched | built by the contract from the goal's registry, package and version | derived |
| the moment a release was seen | the checking transaction's own `datetime` | derived |
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

**The impersonation attempt.** A goal on a release that really exists, `requests 2.31.0`, naming the posting wallet as payee. The real release does not name it.

| step | transaction | result |
|---|---|---|
| Post the goal | [`0xde489490...`](https://explorer-studio-dev.genlayer.com/tx/0xde489490bc78aa68704be7def23a09030731d5facaedcab0ff725721efe8e290) | `requests` `2.31.0`, payee `0xa4Df…e4a0`, one hour |
| Pledge | [`0x6b3c59aa...`](https://explorer-studio-dev.genlayer.com/tx/0x6b3c59aadd9019e928ef4f7e55a59ce95a35cc4ba2b5dc2666ee368c47a16a23) | 0.02 GEN |
| Check the registry | [`0xf14ad542...`](https://explorer-studio-dev.genlayer.com/tx/0xf14ad542f043d23771f83229e97ba5ab880fe060b995cae810e6e65e60814379) | PyPI answered 200 for the version, but **`unclaimed`**: *the release does not name this payee* |
| Claim | [`0x1726af44...`](https://explorer-studio-dev.genlayer.com/tx/0x1726af44c243f7d0614c8129d356b2e35e855a7d84b20b8506a27cfd49bd57a2) | **refused**: not seen in time |
| Refund, after the deadline | [`0x5352fb14...`](https://explorer-studio-dev.genlayer.com/tx/0x5352fb1413d52627e3121f1a72b635b6daac3e69b885db2a6077ddcabc1f91a2) | the pledge back to the backer |

**A release that does not ship in time.** A goal on `requests 99.0.0`, which does not exist.

| step | transaction | result |
|---|---|---|
| Post the goal | [`0x4c9bb53f...`](https://explorer-studio-dev.genlayer.com/tx/0x4c9bb53f184e1927186472d3ae129f2e54bc6a7136e51f3b21cc005fe65083e0) | one-hour deadline |
| Pledge | [`0x5e30971b...`](https://explorer-studio-dev.genlayer.com/tx/0x5e30971bd97b98e0d2d054b707904971e091a8be54d6cd791f57f36ecc9841f6) | 0.02 GEN |
| Check the registry | [`0xcb99a5fb...`](https://explorer-studio-dev.genlayer.com/tx/0xcb99a5fbe26033903865fb014119ec07b48ab6161fdaeb91cbb569ccf0c60cd3) | PyPI answered 404: **`not_yet`**, *the registry has no such version* |
| Refund, too early | [`0xaeddbe48...`](https://explorer-studio-dev.genlayer.com/tx/0xaeddbe48415f9a563fa71324e74fe74dffb1208f6c94a2f688331a5a8f71ff48) | **refused**: the deadline has not passed |
| Endorse on BADGE | [`0x0e48a7f2...`](https://explorer-studio-dev.genlayer.com/tx/0x0e48a7f2f1f4d835feb3a2d365a864fcab7376e5ed85304b85a334d8b5541ee3) | **refused**: the release has not been seen in time |
| Pledge, after the deadline | [`0x6ae414a3...`](https://explorer-studio-dev.genlayer.com/tx/0x6ae414a395eb880351426019034984a1da67ffbc79158f542c42be72f159ba6f) | **refused** |
| Check, after the deadline | [`0xd0bfe926...`](https://explorer-studio-dev.genlayer.com/tx/0xd0bfe9266b9722c694d70d3a356c76bbf8fe48b0d2130a4acf41239e66d13b19) | **refused**: nothing seen now could count |
| Claim, after the deadline | [`0x30e75507...`](https://explorer-studio-dev.genlayer.com/tx/0x30e7550770483f2775bc23e25345a58f33611fbb1f03229fb005fea4328341c1) | **refused** |
| Refund | [`0xfc953f98...`](https://explorer-studio-dev.genlayer.com/tx/0xfc953f989eed6e708c84481e05b449bf06e3d4dc02f8530c6a5cce19eec953ec) | backer **5.217011 → 5.236885 GEN**, the pledge back less gas. POT `committed` back to `0` after both refunds |

**Not shown live:** a paid release. That needs a real package version published with the payee's address in its metadata, which this run did not do. The payout path is covered by the test suite (`test_a_release_seen_in_time_pays_the_payee_everything`), and the registry check behind it is the same one that produced both results above.

**Through the site.** The same lifecycle driven through [shipped-ten.vercel.app](https://shipped-ten.vercel.app/) in a real browser, with a wallet that signs every transaction. The site's own code builds, sends and follows each one to its verdict.

| step | transaction | result |
|---|---|---|
| Post the goal | [`0x8bcacbb5...`](https://explorer-studio-dev.genlayer.com/tx/0x8bcacbb5f4af236ccb0672fc21b369f04f660bc51859dacfd862f4f71c34991d) | `requests` `99.2.0`, one hour |
| Pledge | [`0xceeb339f...`](https://explorer-studio-dev.genlayer.com/tx/0xceeb339f3e1ed5592415766fe72d33d651f0704329eb1947f03ca8a8617da503) | 0.01 GEN |
| Check the registry | [`0xac8a739e...`](https://explorer-studio-dev.genlayer.com/tx/0xac8a739e4f70556d5294543db95871e8171dcc71cc1eaa25b875a42a3933a53a) | PyPI answered 404: **`not_yet`** |
| Refund my pledge, after the deadline | [`0xbb73fb63...`](https://explorer-studio-dev.genlayer.com/tx/0xbb73fb63e8e6610ec1f54145fd448fcfffbe111555d9895e6a7615dba99ce619) | the pledge back to the backer |

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
python -m pytest -q                    # 148 tests, no chain and no network
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
test/                       148 tests
```

## License

MIT
