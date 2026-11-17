# Seal: sealed hang set v4

Sealed 2026-11-17T13:49:36+00:00 (KST), before any run of qnx-doctor or the baselines on this set. 24 scenarios.
Written by an independent author (new session, own worktree on srv1) who opened only qd.h, check.sh, D01 and run_sealed3.sh; the doctor, judge, prompts, results, docs and earlier answer keys were not read.

| What | sha256 |
|---|---|
| answers/labels.json (the whole answer key) | `8ac53be5f50a1be87241caa6de93482d0235f9ec890c266a7450da84d4d74209` |
| pool/ tree | `f8980d454d26da13d47cd852c2dd8af7165819ff246b268201d9c00bf8754190` |
| tests/sealed_hang/common at seal time (shared harness, for information; it may change) | `ea4d53b9b39d1dc2a537a2f37ada78eeb261055ac48311323ae81edcbcb00c1c` |

Harness + doctor main commit at seal time: `6742e2d983ad4908b275ef5339c37c1942982be5`.
Nothing in the harness, judge, prompts or scorer changes after this commit; if it must, the change and reason go in the v4 result document.

Tree hash = sha256 of sorted lines «<relpath> <sha256>» (symlink as «<path> -> <target>»), joined by newlines, no trailing newline (same as v3 SEAL.md).

---

## Correction (2026-11-17, still before any run of qnx-doctor or the baselines)

`pool/common` was a partial copy (only `qd.h`, `check.sh`) made by the independent author, who was given just those two files. The harness needs `hi.c`, `snap.c`, `qd_start.c`, `qd_trace.c` too (the launcher, observer and trace helpers), so every scenario reported «target run did not finish» in the reproducibility check. Fixed by making `pool/common` a symlink to `../../../tests/sealed_hang/common` (the full shared harness), exactly as sealed set v3 does. The harness `common` is explicitly allowed to change (see the table note above).

**The scenarios and the answer key are unchanged by this fix.** Proof:

| What | sha256 |
|---|---|
| answers/labels.json | `8ac53be5f50a1be87241caa6de93482d0235f9ec890c266a7450da84d4d74209` (identical to the seal above) |
| pool/ tree, with common as a symlink (new) | `7a15cda57cde79611359b9fefb73e2dc49e50faa04ad1b23204e1af1d4c4cd24` |
| pool/ scenarios only (every D* file, common excluded) | `547cfa557bc4f3d8af4d71c63e1edf62861185caaf39a190bce40562f80a76d1` |

The pool tree hash changed only because common went from two files to a symlink line; the scenarios-only hash is the stable identity of the test content from here on.
