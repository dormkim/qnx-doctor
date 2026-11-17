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
