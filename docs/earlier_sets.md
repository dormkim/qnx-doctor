# Earlier sets: v3, v4, v5 and the sets before them (development numbers)

Moved here from the README on 2026-11-23, text unchanged except for link paths and the last sentence of the
v4/v5 section. None of these numbers is a claim. The numbers that count are patch set v7 (the gate) and sealed
set v6 (diagnosis and fixes), both in the [README](../README.md#what-we-measured-and-what-got-worse). Paths in
code font are relative to the repository root.

## Sealed set v3 (2026-11-17): the first set we did not write, now a development set

Note of 2026-11-22: the "fixed" counts below and in v4 and v5 come from a verifier that read the message records
once. On dev targets that verifier also accepted fixes whose messages stopped after a few rounds
([what was found and repaired](../bench/V6_GATES_1122.md)). The records cannot show whether a recorded fix had that
shape at run time, so read those counts as "passed the verifier of that day".

How the set was made, before any number:
- An agent that had not read qnx-doctor's source, prompts, verifier or past results wrote 21 QNX 8.0 scenarios and
  their answer key (`bench/sealed_v3_1117/README.md` lists exactly what it read). Names, comments and log lines are
  written as a developer would write them, and some mislead on purpose.
- The answer key and the scenario tree were hashed and committed before any run (`bench/sealed_v3_1117/SEAL.md`,
  commit d9d562b). The scoring rules were committed next (caecd37), then a reproducibility check of the unmodified
  scenarios (b075721). Then one run with four arms. Nothing was tuned on this set.
- 5 of 21 were excluded before scoring, with their reasons; no label was edited (`bench/sealed_v3_1117/excluded.json`).
  Four (q02, q06, q09, q21) because our second observer never returned a second TICK count: it reads logs from the
  disk, and these scenarios load the CPUs above the disk driver. Those four are all of the priority-chain cases, so
  **this set says nothing about priority chains**. One (q16) because a loop that should keep running printed nothing;
  most likely our own harness bug, described below.
- Arms, all with the same model: **ours** (code names the kind from the wait graph; the AI fixes, up to 2 tries);
  **naive** (source and TICK logs only, no `pidin`, no graph, no docs, 1 try); **naive_x2** (naive plus one retry,
  told the rerun's TICK counts and verdict). Every arm's fix goes through the same rerun check.
- Small numbers: 16 scenarios scored, of which 8 are fixable faults, 4 are healthy, 4 are "unknown" (the loop stops,
  but not because of a send cycle, a priority chain or a missing reply).
- "Unknown" for ours: qnx-doctor has no literal "unknown" output yet. It prints "loop not running but no wait cycle
  or chain found" and then does not call the AI; the scoring rule committed before the run reads that as "cannot tell".

| arm | kind found | deadlock | missing reply | healthy left alone | unknown said "cannot tell" | false alarm on healthy | fixed (rerun-proven) | "fixed" on an unknown case | false fix |
|---|---|---|---|---|---|---|---|---|---|
| ours | 13/16 | 4/5 | 3/3 | 3/4 | 3/4 | 1/4 | 3/8 | 0 | 0 |
| naive | 12/16 | 5/5 | 3/3 | 4/4 | 0/4 | 0/4 | 2/8 | 2 | 0 |
| naive_x2 | 11/16 | 4/5 | 3/3 | 4/4 | 0/4 | 0/4 | 3/8 | 3 | 0 |

Source: `results/sealed3_20261117/score.md` (copied from the run; per-axis table and literal outputs are there).

What held:
- On the 4 unknown cases the baselines named a hang kind every time. On the two whose cause is outside the given
  sources (q12: a server waits for a signal from a supervisor that is not in the scenario; q17: it waits for a
  semaphore an external calibration tool should post), both baselines deleted the wait or posted the semaphore
  themselves, and the rerun check accepted it because the loop ran again. ours made no fix on any unknown case.
- False fixes on healthy programs: 0 in every arm.

What got worse, or did not get better:
- **Fix rate is a tie** with the same-retry baseline: 3/8 and 3/8, the same three scenarios. On this set the wait
  graph and the docs added no fixes over a second try.
- **One false alarm on a healthy program** (q19), baselines 0. A server holds each reply until a periodic pulse, so
  every snapshot shows the client REPLY-blocked on a server waiting in RECEIVE: the picture of a missing reply. The
  client was still printing TICKs. Our judge looks at thread states, not at whether the TICK count grows.
- **One missed deadlock** (q10), naive 5/5. The most likely cause is our harness: the recorder we link into every
  scenario (`common/qd_trace.c`) made its own kernel calls between the program's `TimerTimeout()` and its
  `MsgReceive`, so the timeout was used up, the program never reached the deadlock, and the snapshot showed no cycle.
  The baselines named the deadlock from the source. The same bug can affect q13 and q16 (the other two scenarios
  that use `TimerTimeout`). A fix is now on `main` (merged from `fix/trace-timertimeout`); it was checked on a new
  harness test, not on this set.
- **One unknown case called healthy** (q11, a CPU spin): the loop had printed TICKs before it stopped, and the code
  treats "some TICKs" as running.

We do not rerun v3 with any of these fixes. They were to be measured on a new sealed set (v4), written by a new author,
sealed before the run and run once. Analysis: [docs/analysis_sealed3_1117.md](analysis_sealed3_1117.md).

## After v3: sealed sets v4 and v5 (run 2026-11-18), now development sets

The fixes for the v3 failures are on `main`, checked only on new harness tests (`tests/harness_checks/`) and unit
tests, never on v3:
- the recorder re-arms the program's `TimerTimeout` right before the real call (q10, q16);
- the observer counts TICKs twice in the same boot, and the reproducibility check uses those two counts instead of a
  second observer that hung under a CPU load above the disk driver (the 4 excluded chain scenarios); `/tmp` is in RAM;
- the judge checks progress: a waiter whose loop keeps ticking is not hung, and "healthy" needs the count to grow
  (q19 false alarm, q11 called healthy);
- the tool says `unknown` itself (spinning on the CPU, blocked outside message passing, or not enough information)
  and still calls no AI and claims no fix in that case.

None of this is a v3 result. v4 was written by a new author who had not seen the code, sealed and run once on
2026-11-18 ([plan](../bench/V4_PLAN.md), [result](../bench/sealed_v4_1117/RESULT_1118.md)); v5, written by the main session
after a harness fix, was run once the same day ([result](../bench/sealed_v5_1118/RESULT_1118.md)). Both have been opened
and read case by case since, so (corrected 2026-11-21) **v3, v4 and v5 are now used as development sets**: changes
are tried on their records ([bench/DEVSET_RECALC_1121.md](../bench/DEVSET_RECALC_1121.md)) and none of those numbers
is a claim. The numbers that count are patch set v7 and sealed set v6, in the [README](../README.md#what-we-measured-and-what-got-worse).

## Earlier sets (shaped by people who knew the code)

These came first and were written by the same people who wrote qnx-doctor: the generators, the verifier, the
baseline prompt and the scorer. The verifier rule was changed once after looking at v1 results. Read them as
development numbers.

- `tests/sealed_hang/`: 7 hand-written scenarios, sealed before the judge existed (file names hint at the bug).
- `tests/gen_hang/` v1 (20 held-out seeds) and v2 (30 held-out seeds, `sealed2.json`): seeded random generators with
  decoys, run-time wiring and priorities. On v2 every arm named all 30 kinds. Fixed on the first try: ours 24/25,
  naive 20/25 (ours could also retry, 25/25; the naive arm had one try, so "25 vs 20" mixes two effects). Records:
  [docs/measure_structure_1116.md](measure_structure_1116.md), [docs/measure_holdout_1116.md](measure_holdout_1116.md).
- None of these sets use `TimerTimeout`, so the recorder bug above does not touch them.
