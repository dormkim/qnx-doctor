# sealed hang v4 — reproducibility result (2026-11-18)

States only (QNX licence 4.6(i)). No doctor, judge, prompt or scorer output here.

## First pass (2026-11-17): stopped by the stop rule

`QD_SMP` default (2 cores), `repro_v3.py --same-boot`: **19/24 agree**; 5 disagreed, all "expected stops, kept ticking":
D08, D13, D17, D23 (priority_chain) + D20 (multi). Per V4_PLAN ("≥2 priority_chain fail reproduction → harness failure, not scored"), the run was stopped and **not scored** (commit `343ccfc`).

## Diagnosis (2026-11-18): the scenarios could not hang as written

Confirmed by `pidin`:
- `name_attach()` ignores its `flags` arg (QNX lib ref: "Currently not used") → the "fixed-priority" servers inherited the client's priority (observed `30r`), beat the hog, served every request. (D08, D13, D20, D23)
- D17's `PTHREAD_PRIO_PROTECT` ceiling-15 refuses a prio-30 locker (`EINVAL`) → the high thread never blocked (observed `30f NANOSLEEP`). Priority ceiling cannot produce this inversion; the label was impossible.
- On 2 cores one mid hog cannot starve a low server (spare core).

Full detail and the fix: `SEAL.md` → "Correction 2".

## Fix + second pass (2026-11-18): all reproduce

- `qd.h`: genuine fixed-priority endpoint via `ChannelCreate(_NTO_CHF_FIXED_PRIORITY)` (`qd_fixed_chan`/`qd_open_fixed`).
- D08/D13/D20/D23: one-line swaps (labels unchanged).
- D17: rewritten to classic `PRIO_NONE` priority inversion; label corrected (kind/expect unchanged).
- Target single-core (`QD_SMP=1`).

`QD_SMP=1 python3 bench/repro_v3.py bench/sealed_v4_1117/pool bench/sealed_v4_1117/answers/labels.json out.json --same-boot`

**24/24 agree, 0 errors, 0 missing counts.** Stop rule not triggered. The set is run-verified.

Representative counts (snap == later, i.e. no progress = hung as labeled):
- D08 client/server 0, hog 1 · D13 all stages 0, hog 1 · D20 all 0, hog 1 · D23 0, hog 1
- D17 high 1 (blocked before its post-lock tick), low 2 (holds mx, preempted), hog 1

## Scoring gate

The single scored run (code / ours / naive / naive_x2) stays gated on explicit user confirmation and must set `QD_SMP=1`.
