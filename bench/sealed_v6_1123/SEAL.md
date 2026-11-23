# Seal: sealed hang set v6

Sealed 2026-11-23 (KST), before any run of qnx-doctor or the baselines on this set, and before the reproducibility
check. **30 scenarios.** Freeze commit: `926a716269af5ea773d8cf82ccab2789f8f7097e` (tag `v6-freeze`, bench/FREEZE_V6.md).

Written by a fresh agent that had not seen this repository's code, in a sparse worktree holding only
`tests/sealed_hang/common/`, `tests/sealed_hang/D01/` and `bench/run_sealed3.sh`, from the brief of
bench/V6_PLAN.md section 3. Its README lists the files it opened. Nothing was compiled or run by the author.
The maintainer checked only structure before sealing: 30 ids in pool and key, the mix of section 3, the required
fields, the state words, `pool/common` identical to `tests/sealed_hang/common`, no answer words in the pool.

| What | sha256 |
|---|---|
| answers/labels.json | `5865c5e7bba1a391d31f2b7c65a1c75a33bdf1d6e1cd494ea488810f362cc271` |
| pool (tree, with common) | `2082239dcb5257301471490cddb3b609e773550aff204a55943bb1d9590a2bfe` |
| pool (tree, without common) | `b733ebb540aaef5e1debf44bdcbc3859241e947c01d45148433c56f7d3fb85ea` |

Tree hash: `python3 bench/seal_hash.py tree <pool> [--no-common]` (sorted «<relpath> <sha256>» lines).

Next, unchanged from V6_PLAN section 4: reproducibility check `bench/repro_v3.py POOL LABELS OUT --same-boot`;
a failing scenario goes back to the author once with only the unseen state words; a second failure excludes it,
and the key is never edited.

## Reproducibility check, 2026-11-23

`bench/repro_v3.py ... --same-boot` (with `bench/repro_states.py`) at the seal commit, QD_SMP=1, no doctor, no AI:
**30 of 30 agree** on both the TICK expectation per role and the thread states named in the key. No scenario went
back to the author and none is excluded. Record: `repro_v6.json`.
