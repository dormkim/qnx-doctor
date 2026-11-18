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

---

## Correction 2 (2026-11-18, still before any scored run of qnx-doctor or the baselines)

The reproducibility check (`bench/repro_v3.py --same-boot`) found that the five priority scenarios did **not** reproduce their labels: the "low fixed-priority server" never got starved and the high waiter kept ticking. Root cause, confirmed by `pidin` (states only, QDL 4.6(i)):

1. **`name_attach()` ignores its `flags` argument.** QNX lib ref (`name_attach.html`): the `flags` parameter is *"Currently not used"*, and the channel is always created with `_NTO_CHF_COID_DISCONNECT | _NTO_CHF_UNBLOCK | _NTO_CHF_DISCONNECT` only. So `name_attach(NULL, me, _NTO_CHF_FIXED_PRIORITY)` created an ordinary channel; its receiver **inherited the caller's priority**. The prio-12 server ran at the prio-30 client's priority (observed `30r`), beat the prio-20 hog, and served every request — no starvation. This hit D08, D13, D20, D23 (all used `name_attach(..._NTO_CHF_FIXED_PRIORITY)`).
2. **A priority-ceiling mutex cannot produce this hang (D17).** With `PTHREAD_PRIO_PROTECT` ceiling 15, a prio-30 locker is refused (`EINVAL`), so the high thread never blocks (observed `30f NANOSLEEP`, ticking freely); raising the ceiling to ≥30 would boost the holder above the hog, so no starvation either. Priority ceiling is an inversion-*prevention* mechanism — "ceiling too low" is not a reachable hang. The label encoded an impossible QNX behaviour.
3. **One mid hog cannot starve on 2 cores.** The target booted `-smp 2`; even with a genuinely fixed-priority server at prio 12, the server runs on the spare core and serves the client. The author's design (one hog) is single-core.

### Fix applied (by the main session, documented here; verified by running, not by design)

- **Harness (`common/qd.h`)**: added `qd_fixed_chan()` / `qd_open_fixed()` — a genuinely fixed-priority endpoint via `ChannelCreate(_NTO_CHF_FIXED_PRIORITY | ...)` (which *does* honour the flag), publishing `pid+chid` at `/tmp/<name>.id` so peers connect by `ConnectAttach`. `common` is explicitly allowed to change.
- **D08, D20, D23** (`lowfix_srv.c`, clients) and **D13** (`chain_s2.c`, `chain_s1.c`): one-line swaps from the broken `name_attach(..._NTO_CHF_FIXED_PRIORITY)` / `qd_open` to the helpers. The scenario shape and each label's described mechanism ("fixed-priority channel breaks inheritance") are preserved and now actually hold.
- **D17** (`prio_ceiling.c`): rewritten from the unsound `PRIO_PROTECT` ceiling to the classic `PTHREAD_PRIO_NONE` priority inversion (no inheritance; low holder preempted by the mid hog; high waiter blocked). **Its label was corrected** to match (category/axes/states/culprit/fix/design); `kind` (priority_chain), `members`, `loop_logs`, and `expect` (all "stops") are unchanged.
- **Target single-core**: the v4 run boots with `QD_SMP=1` (env read by `bin/qd-target-exec`; default stays 2 for other uses). Rationale: priority-inversion starvation with one mid-priority load is a uniprocessor phenomenon, matching the author's one-hog design and single-core ASIL-D partitions.

**Why the main session (not the independent author) applied it:** the fixes are objective QNX-correctness changes whose target is each label's *pre-existing* described state, verified by running (`pidin` + TICK growth), not by matching the doctor. Label independence is preserved for D08/D13/D20/D23 (their answer text is unchanged); D17's label was factually impossible and was corrected to a textbook-correct inversion. No scored run has happened, so nothing could be tuned to a result.

### Result: all 24 reproduce

`QD_SMP=1 python3 bench/repro_v3.py pool answers/labels.json out.json --same-boot` → **24/24 agree**, 0 errors. The stop rule (≥2 priority_chain failing → not scored) is **not** triggered. The set is now run-verified.

### New hashes (changed by this correction)

| What | sha256 | vs. seal |
|---|---|---|
| answers/labels.json | `2606a8565ea997a4648596f43b6f2ef6694e1bce77c2fa0e5ff4fd7d028d9d52` | changed (D17 diagnosis only) |
| pool/ scenarios only | `f7ff9dd91992a6753656d67242461fe244ac50b29d400ee81d3306c88d9ecf90` | changed (4 one-line swaps + D17 rewrite) |
| pool/ tree | `a9b77b0e0f5de3ddbf7068581fcf30d7fc619bd369258fc73e0d0abd97b5c54f` | changed |
| tests/sealed_hang/common tree | `29b290d53e7ec77c02d70424a8fb3e8ed327eb979e6bbd9d5a8574adb58d0024` | changed (qd.h helpers) |

The scored run must set `QD_SMP=1`. The commit carrying this correction is recorded in `repro_result_1117.md`.
