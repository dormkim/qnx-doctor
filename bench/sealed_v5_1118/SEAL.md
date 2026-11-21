# Seal: sealed hang set v5

Sealed 2026-11-18 (KST), before any run of qnx-doctor or the baselines on this set. **12 scenarios.**

## Why v5 exists
v4 scored priority_chain 0/5 because the shared harness could not form the inversion: `qd_fixed_chan()` published
its id file with a `rename()`; in our runs the renamed file never appeared under `/dev/shmem`, so the client never connected and never sent
(v4 SEAL.md Correction 3). The detector (`waitgraph.inversions`) was correct the whole time. v5 re-measures the
provable priority-inversion detector on a **fresh set, with the harness fixed**, scored single-core.

## Composition (kinds)
| kind | ids | n |
|---|---|---|
| priority_chain | E01 (classic 30/12/20), E02 (wide gap 40/3/20), E03 (two waiters 28·32 on one prio-10 server), E04 (two hogs 20·22) | 4 |
| deadlock | E05 (2-node send cycle), E06 (3-node send ring) | 2 |
| missing_reply | E07 (good path forgets MsgReply), E08 (stops replying after 3) | 2 |
| healthy | E09 (normal request/reply), E10 (healthy + a harmless prio-5 load below the server) | 2 |
| unknown | E11 (CPU spin, no message), E12 (semaphore never posted, no message edge) | 2 |

The honesty controls (healthy ×2, unknown ×2) exist so an arm that *guesses* a kind is punished by false alarms:
E10 is a load-plus-server that a naive reading can mistake for a chain; E11/E12 are non-message-passing hangs that
a guesser may label deadlock/chain. A tool that only claims what it can prove should keep these as healthy/unknown.

## Independence & freezing
- **Detector frozen before authoring.** `waitgraph.py` (cycles / inversions / missing_replies / judge) was committed
  at `647c90d` *before* any v5 scenario was written and is **unchanged** by v5. It is not tuned on this set.
- Authored by the main session (not a separate author), composing v4's **proven** non-priority patterns (ring,
  half-reply, relay, spin) with **fresh** priority-inversion scenarios built on the fixed `qd_fixed_chan`. This is
  disclosed, as in v4: the scenarios are objective QNX constructions whose labels describe their pre-existing states,
  verified by running (`pidin` + TICK growth), not by matching the doctor. No scored run has happened, so nothing
  could be tuned to a result.
- **Own copy of `common/`** (a real directory, not a symlink to `tests/sealed_hang/common`), so later edits to the
  canonical harness cannot change v5's sealed bytes.

## Reproducibility (before the scored run)
`QD_SMP=1 python3 bench/repro_v3.py bench/sealed_v5_1118/pool answers/labels.json repro_v5.json --same-boot`
→ **12/12 agree**, 0 errors. Every unmodified scenario does what its label's `expect` says (per role: stops / ticks).
The stop rule (≥2 priority_chain failing → not scored) is not triggered.

## Hashes
| What | sha256 |
|---|---|
| answers/labels.json | `0ad4dae3cb8603e25f1f3503dd4143e06a6037917b0965db08315c0b5a5f1874` |
| pool/ scenarios only (every E* file, common excluded) — the stable identity of the test content | `6342aa113e7e6e5a6d88bd6eb2dca53a031bc98ac70e121950d3fd40916a7464` |
| pool/ tree (incl. the real common copy) | `91d82c2128f81b6ab426fbbfe354c925c1d6a7aa299be47d01edfcfec5b557cc` |
| pool/common tree (v5's own frozen harness, with the rename fix) | `86c7d96d27f3a96efedbd710c5e99a6164795fd8abee4a4858cca7e3a7984086` |

Harness + doctor main commit at seal time: `647c90d5f9287216776104fe09dc1e88b80c8283`.
Nothing in the harness, judge, prompts or scorer changes after this commit; if it must, the change and reason go in
the v5 result document.

Tree hash = sha256 of sorted lines «<relpath> <sha256>» (symlink as «<path> -> <target>»), joined by newlines, no
trailing newline (same as v3/v4). Verified: this script reproduces v4's recorded `f7ff9dd9…` (scenarios-only) and
`2606a856…` (labels) exactly.

## The scored run
Single run, 4 arms (code / ours-ai / naive / naive_x2), **`QD_SMP=1`**, scored once with `bench/score_structure.py`.
Any post-seal change to harness/scorer is documented in the v5 result document.
