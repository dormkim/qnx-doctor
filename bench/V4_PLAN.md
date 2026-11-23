# Sealed set v4: plan (written 2026-11-17, before the set exists)

v4 is where the fixes made after v3 are measured, and the only place. v3 is not rerun or rescored with them
(docs/분석_sealed3_1117.md §0). This plan is fixed now so that the set is not shaped by what the fixes need.

## What v4 has to answer

Changes since v3 (all on `main` before v4 is written; the harness commit is named in v4's SEAL.md):

| id | change | v3 failure it targets |
|---|---|---|
| H1 | `qd_trace.c` re-arms the program's `TimerTimeout` right before the real call | q10 missed deadlock, q16 excluded (both likely) |
| H2 | snap counts TICKs twice in the same boot (`TICKS2`); the reproducibility check uses those two counts (`repro_v3.py --same-boot`) instead of a second observer; `/tmp` is a RAM link (`check.sh`) | 4 chain scenarios excluded (second observer hung) |
| H3 | pidin lines of every program are kept when the judge finds nothing | analysis stuck at «likely» |
| J1 | progress check: a waiter whose loop keeps ticking is not hung; «healthy» needs growth | q19 false alarm, q11 called healthy |
| J2 | explicit `unknown` output (spinning / blocked outside message passing / not enough information); no AI, no fix | «cannot tell» was only a note |

Questions, in this order:
1. Does the harness reproduce priority chains and `TimerTimeout` cases as their author meant (reproducibility check,
   before the run)? If not, v4 says nothing about them, as v3 said nothing about chains.
2. On healthy programs that look stuck in a snapshot (slow replies, long polls): false alarms, ours vs baselines.
3. On stops outside the vocabulary: does ours say «unknown», and do the baselines «fix» what the evidence does not
   support?
4. Fixes, rerun-proven, ours vs naive_x2, first try and with retries. A tie is a possible result and is reported.

## Who writes it

A fresh agent in a new session, with no memory of this repository's work, in its own worktree on the build server. It must not
open: `qnx_doctor/`, `bench/` (except `run_sealed3.sh` to see how scenarios are started), `results/`, `runs/`,
`docs/`, `JUDGES.md`, `README.md`, this file, `tests/harness_checks/`, earlier answer keys, or the v3 pool. It gets the
**author brief** below, plus the format files `tests/sealed_hang/common/{qd.h,check.sh}` and one example scenario
(`tests/sealed_hang/D01`). Its README lists every file it opened (as v3's did); the session transcript is kept.

Author brief (pasted as is):
- Write 24 QNX 8.0 message-passing scenarios and an answer key in `bench/sealed_v4_<date>/{pool,answers}`, in the
  format of `tests/sealed_hang` (programs include `../common/qd.h`; `run.sh` starts them from `/var/qd/<id>/` and
  sleeps 4 s). Ids are shuffled; names, comments and log lines read like a developer's, some mislead on purpose.
- Format rule: a loop program writes `TICK <role> <n>` to `/tmp/d0<role>.log`, where `<role>` is the program's file
  name, a running loop prints a TICK at least every 500 ms, and a program that ends on purpose prints no TICK.
- Mix (at least): 4 deadlock, 5 priority chain, 3 missing reply, 5 healthy (at least 2 that look stuck in a snapshot
  but keep ticking), 5 unknown (at least 1 loop that stops by spinning on the CPU, 1 that blocks outside message
  passing, 2 whose cause is not in the sources: `info_insufficient: true`), 2 multi-cause. At least 4 scenarios use
  `TimerTimeout`, spread over at least 3 kinds. The labels carry `kind`, `accept_kinds`, `loop_logs`, `axes`,
  `expect` per role (`stops` / `ticks` / `any`), as in v3.
- Public QNX knowledge and common bug patterns only.

## How it is sealed and run

1. **Seal** (commit 1): sha256 of `answers/labels.json` and of the pool in `SEAL.md`, plus the `main` commit of the
   harness and doctor. Nothing in the harness, judge, prompts or scorer changes after this commit. If something must,
   the change and the reason go into the result document.
2. **Rules** (commit 2): the v3 rules unchanged (`bench/sealed_v3_1117/README.md`); `score_structure.py` already
   reads the explicit `unknown`. Decided now: if 2 or more priority-chain scenarios fail reproduction for a harness
   reason, the run is stopped and reported as a harness failure, not scored.
3. **Reproducibility check** (commit 3), no doctor: each unmodified scenario against its `expect`, with the H2
   harness: `bench/repro_v3.py POOL LABELS OUT --same-boot` (snap's own two counts in one boot; no second observer).
   Disagreements are excluded with their reason; labels are not edited.
4. **Run once**: `bench/run_sealed3.sh` with the four arms (code, ours, naive, naive_x2), same model, one QEMU at a
   time. The script refuses an output directory that was used before.
5. **Report**: v4 table next to the v3 table copied unchanged, the list of changes above, exclusions, per-axis table,
   «fixed on unknown» listed for a person to read, first try vs retries. States only, no QNX timing numbers
   (licence 4.6(i)). Then the failure analysis, as for v3.

## When

| date | step |
|---|---|
| 11/18 | brief the author; author writes the set |
| 11/19 | seal (commit 1), rules (commit 2) |
| 11/20 | reproducibility check (commit 3); stop rule in step 2 applied |
| 11/21 | single run, score, result document, README and JUDGES.md updated |
| before 11/22 | everything above committed and pushed |

## Known limits going in

- The progress check counts TICKs twice, about two seconds apart, in one boot. A loop slower than that looks stopped; the
  500 ms format rule is there for that reason.
- A waiter is matched to its TICK log by program name. A loop whose log name differs from its program name still
  counts for «healthy», but a slow wait in it is not excused.
- Two processes of the same program share one TICK log; if it grows, a wait in either is excused.
- Why the v3 second observer hung (after its fork, before pidin finished) is not confirmed; v4 no longer depends on it.
- The `TimerTimeout` re-arm restores a timeout that QNX would have dropped if the program made another, unwrapped
  kernel call in between. No scenario so far does that.
