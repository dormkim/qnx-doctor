# Development-set recalculation (2026-11-21)

**Not a result and not a claim.** Sealed sets v3, v4 and v5 were each run once (2026-11-17/18) and have since been
read case by case, so they are development sets now. This page applies three changes made on 2026-11-21 to their
**recorded** runs. No boot, no AI call, no new observation: only the states kept in the jsonl records. The recorded
score tables (`results/sealed3_20261117/score.md`, `bench/sealed_v4_1117/scored_1118/score.md`,
`bench/sealed_v5_1118/scored_1118/score.md`) are not replaced. A number for a claim is measured once on a new
sealed set (`bench/V6_PLAN.md`). States only, no timing (QNX licence 4.6(i)); TICK counts below are used as
«stopped / ticking / more than before», not as rates.

Reproduce: `python3 bench/rejudge_records.py` and `python3 bench/score_structure.py ...` (no SDK needed).

## 1. Liveness rule (`qnx_doctor/hangdoctor.py`, `not_restarted`)

Before: «alive again» needed at least one role that had printed **no TICK at all** at the first observation and
printed 2 or more in the rerun. A ring whose members each print one TICK before the first send, or a server that
stops replying after a few rounds, has no such role, so no fix by any arm could pass.

Now: a role counts as **stopped** if its TICK count did not grow between the two counts of the first observation
(flat, idle or missing). At least one stopped role must print 2 or more TICKs **more than it had**, and, when the
rerun has a second count, still be ticking between the rerun's two counts. Unchanged: no cycle or chain in the
rerun, no loop that had ticked goes silent, no process gone, same message structure (`structure.compare`).
A failed try is told which condition failed instead of «still hung: no wait cycle and no priority chain».

### Recorded reruns judged again, all three arms with the same rule

| set | arm | fixed, as recorded | fixed, current rule | first try fixed, before -> after | false fix (healthy label) | fixed on unknown label | shortcut rejected |
|---|---|---|---|---|---|---|---|
| v3 | ai | 3/8 (of labels with something to fix: 3/8) | 3/8 | 3 -> 3 | 0 -> 0 | 0 -> 0 | 0 -> 0 |
| v3 | naive | 2/8 (of labels with something to fix: 2/8) | 2/8 | 2 -> 2 | 0 -> 0 | 2 -> 2 | 0 -> 0 |
| v3 | naive_x2 | 3/8 (of labels with something to fix: 3/8) | 3/8 | 3 -> 3 | 0 -> 0 | 3 -> 3 | 1 -> 1 |
| v4 | ai | 5/19 (of labels with something to fix: 5/14) | 6/14 | 5 -> 6 | 0 -> 0 | 0 -> 0 | 0 -> 0 |
| v4 | naive | 4/19 (of labels with something to fix: 4/14) | 5/14 | 4 -> 5 | 0 -> 0 | 0 -> 0 | 0 -> 1 |
| v4 | naive_x2 | 5/19 (of labels with something to fix: 5/14) | 6/14 | 5 -> 6 | 0 -> 0 | 0 -> 0 | 0 -> 5 |
| v5 | ai | 4/10 (of labels with something to fix: 4/8) | 7/8 | 4 -> 7 | 0 -> 0 | 0 -> 0 | 0 -> 0 |
| v5 | naive | 4/10 (of labels with something to fix: 4/8) | 7/8 | 4 -> 7 | 0 -> 0 | 0 -> 0 | 0 -> 0 |
| v5 | naive_x2 | 4/10 (of labels with something to fix: 4/8) | 7/8 | 4 -> 6 | 0 -> 0 | 0 -> 0 | 0 -> 0 |

Read this table with these limits:
- The «after» column is an **upper bound**. The records do not hold the rerun's second TICK count (kept only since
  2026-11-21), so the «still ticking at the second count» part of the new rule could not be applied; only «2 or
  more TICKs more than before». The baseline rows also lack the process count after the rerun; it is taken as
  unchanged (a process that went away is still caught by the recorded structure reason).
- **All arms rise together** (v4: +1 each, D03; v5: +3 each, E05, E06, E08). The change says nothing about ours
  against the baseline. Fixed stays a tie in every set: v3 3 : 3 (naive_x2), v4 6 : 6, v5 7 : 7.
- v3 does not change and cannot: its records have no progress, so the rule reads them as before.
- naive_x2's first-try count rises less in v5 (4 -> 6) because its first try on E08 was not applied (edit text not
  found); its second try is the one that now passes.
- What is still not fixed in v5 by any arm: E04. Its recorded first observation does not show the wait its label
  describes (section 3).

### Attempts whose verdict changed
| set | arm | id | label | try | alive | fixed | structure reasons recorded | TICKs first -> rerun |
|---|---|---|---|---|---|---|---|---|
| v4 | ai | D03 | deadlock | 1 | False -> True | False -> True | - | {"d003c": 1, "d003b": 1, "d003a": 1} -> {"d003c": 212493, "d003b": 212494, "d003a": 212493} |
| v4 | naive | D03 | deadlock | 1 | False -> True | False -> True | - | {"d003c": 1, "d003b": 1, "d003a": 1} -> {"d003c": 200697, "d003b": 200697, "d003a": 200697} |
| v4 | naive | D10 | deadlock | 1 | False -> True | False -> False | non-messaging process changed its threads' priority or load: /var/qd/D10/abba d010a d010b [[10, False]] -> [[10, False], [10, False], [10, False]] | {"d010b": 2, "d010a": 2} -> {"d010b": 34, "d010a": 35} |
| v4 | naive_x2 | D02 | priority_chain | 2 | False -> True | False -> False | non-messaging process changed its threads' priority or load: /var/qd/D02/prio_none d002a d002b d002c [[10, True], [20, True], [40, False]] -> [[10, True], [20, True], [30, False], [40, False]] | {"d002c": 1, "d002b": 1, "d002a": 2} -> {"d002c": 40, "d002b": 1, "d002a": 2} |
| v4 | naive_x2 | D03 | deadlock | 1 | False -> True | False -> True | - | {"d003c": 1, "d003b": 1, "d003a": 1} -> {"d003c": 197092, "d003b": 197093, "d003a": 197092} |
| v4 | naive_x2 | D10 | deadlock | 1 | False -> True | False -> False | non-messaging process changed its threads' priority or load: /var/qd/D10/abba d010a d010b [[10, False]] -> [[10, False], [10, False], [10, False]] | {"d010b": 2, "d010a": 2} -> {"d010b": 34, "d010a": 35} |
| v4 | naive_x2 | D10 | deadlock | 2 | False -> True | False -> False | non-messaging process changed its threads' priority or load: /var/qd/D10/abba d010a d010b [[10, False]] -> [[10, False], [10, False], [10, False]] | {"d010b": 2, "d010a": 2} -> {"d010b": 34, "d010a": 35} |
| v4 | naive_x2 | D17 | priority_chain | 2 | False -> True | False -> False | non-messaging process changed its threads' priority or load: /var/qd/D17/prio_ceiling d017a d017b d017c [[10, True], [20, True], [40, False]] -> [[10, True], [20, True], [30, False], [40, False]] | {"d017c": 1, "d017b": 1, "d017a": 2} -> {"d017c": 40, "d017b": 1, "d017a": 2} |
| v4 | naive_x2 | D22 | deadlock | 2 | False -> True | False -> False | non-messaging process changed its threads' priority or load: /var/qd/D22/selfsend d022a [[10, False]] -> [[10, False], [10, False]] | {"d022a": 1} -> {"d022a": 41} |
| v5 | ai | E05 | deadlock | 1 | False -> True | False -> True | - | {"d0e05b": 1, "d0e05a": 1} -> {"d0e05b": 326639, "d0e05a": 326638} |
| v5 | ai | E06 | deadlock | 1 | False -> True | False -> True | - | {"d0e06c": 1, "d0e06b": 1, "d0e06a": 1} -> {"d0e06c": 216751, "d0e06b": 216750, "d0e06a": 216750} |
| v5 | ai | E08 | missing_reply | 1 | False -> True | False -> True | - | {"d0e08a": 3, "d0e08b": 4} -> {"d0e08a": 34, "d0e08b": 34} |
| v5 | naive | E05 | deadlock | 1 | False -> True | False -> True | - | {"d0e05b": 1, "d0e05a": 1} -> {"d0e05b": 304957, "d0e05a": 304958} |
| v5 | naive | E06 | deadlock | 1 | False -> True | False -> True | - | {"d0e06c": 1, "d0e06b": 1, "d0e06a": 1} -> {"d0e06c": 215698, "d0e06b": 215697, "d0e06a": 215697} |
| v5 | naive | E08 | missing_reply | 1 | False -> True | False -> True | - | {"d0e08a": 3, "d0e08b": 4} -> {"d0e08a": 34, "d0e08b": 34} |
| v5 | naive_x2 | E05 | deadlock | 1 | False -> True | False -> True | - | {"d0e05b": 1, "d0e05a": 1} -> {"d0e05b": 300063, "d0e05a": 300063} |
| v5 | naive_x2 | E06 | deadlock | 1 | False -> True | False -> True | - | {"d0e06c": 1, "d0e06b": 1, "d0e06a": 1} -> {"d0e06c": 216443, "d0e06b": 216443, "d0e06a": 216444} |
| v5 | naive_x2 | E08 | missing_reply | 2 | False -> True | False -> True | - | {"d0e08a": 3, "d0e08b": 4} -> {"d0e08a": 34, "d0e08b": 34} |

Every attempt that is newly «fixed» has no structure reason, a hang label (never healthy or unknown), a rerun graph
without cycle or chain, and the same process count where it was recorded. The baseline attempts that are newly
«alive» but still not fixed (D02, D10, D17, D22) are stopped by a recorded structure reason about thread counts.
That reason may itself be an artifact: the structure record is built from the strict pidin parse, which drops
threads in a MUTEX wait, so the first observation counted fewer threads than the program had. Whether those baseline
fixes were real is **not known** from the records; it is listed as an open item in `bench/V6_PLAN.md`.

### Fake fixes (must stay rejected)

| check | result |
|---|---|
| Recorded target runs of `bench/fake_fix_check.py` (dev pool, 2026-11-16, two runs, 2 real + 6 fake fixes each), judged again with the current rule (`rejudge_records.py --fake`) | 12 of 12 fake fixes rejected. 3 of 4 real fixes fixed; the fourth was already rejected in its own recording (the hung boot had lost its client, `docs/measure_structure_1116.md` caveats) |
| Unit tests, old shapes (`tests/unit/test_verdict.py` FakeFixes, 10 cases) | pass unchanged |
| Unit tests, new shapes (StoppedAfterTicking, 13 tests): same single TICK again, one more TICK, more TICKs then stopped again, loop deleted, a member quits, one loop runs while another goes silent, cycle still there, healthy first run, the witness is a loop that never stopped | every fake shape rejected; the real shapes (ring that ticked once, server that stopped after a few rounds) pass |
| Structure check (`tests/unit/test_structure.py`) | unchanged, passes |
| Dev-set records: «fixed» on a healthy label / on an unknown label, before -> after | 0 -> 0 in v4 and v5 for every arm; v3 unchanged (baselines 2 and 3 on unknown labels, ours 0) |

Limit: the recorded fake fixes all come from scenarios whose roles printed no TICK before the hang, so they
exercise the rule exactly as the old one did. The new part (stopped after ticking) is covered by unit tests only.
`fake_fix_check.py` has **not** been rerun on a target with a ring that ticks before it hangs; that needs a boot
and is a gate before v6 is sealed (`bench/V6_PLAN.md`).

## 2. Scorer (`bench/score_structure.py`)

Two errors, fixed before v6 is sealed:
- a «healthy» label was hit only by the literal word «healthy», which no arm has (they say `none`), so the healthy
  column read 0/5 and 0/2 for every arm; a v3 label `none` crashed the scorer outright since the v4 vocabulary change
  (5 unit tests had been failing since then);
- the «fixed» denominator held the healthy labels.

The recorded runs under the corrected scorer (liveness rule as recorded, i.e. before section 1):

| set | arm | kind found (recorded -> corrected) | healthy (recorded -> corrected) | fixed (recorded -> corrected denominator) |
|---|---|---|---|---|
| v3 | ours | 13/16 -> 13/16 | 3/4 -> 3/4 | 3/8 -> 3/8 |
| v3 | naive | 12/16 -> 12/16 | 4/4 -> 4/4 | 2/8 -> 2/8 |
| v3 | naive_x2 | 11/16 -> 11/16 | 4/4 -> 4/4 | 3/8 -> 3/8 |
| v4 | ours | 12/24 -> 17/24 | 0/5 -> 5/5 | 5/19 -> 5/14 |
| v4 | naive | 13/24 -> 18/24 | 0/5 -> 5/5 | 4/19 -> 4/14 |
| v4 | naive_x2 | 11/24 -> 16/24 | 0/5 -> 5/5 | 5/19 -> 5/14 |
| v5 | ours | 10/12 -> 11/12 | 0/2 -> 1/2 | 4/10 -> 4/8 |
| v5 | naive | 8/12 -> 10/12 | 0/2 -> 2/2 | 4/10 -> 4/8 |
| v5 | naive_x2 | 8/12 -> 10/12 | 0/2 -> 2/2 | 4/10 -> 4/8 |

v3 was scored with the older scorer, which was right on both points, so it does not move. In v4 the baseline is
ahead on kind found (18 : 17) as it was before. In v5 ours misses one healthy label (E10: a CPU-load role that
prints one TICK and then spins is reported as `unknown (spinning)`), so the gap shrinks from 10 : 8 to 11 : 10, and
that one point is the two «unknown» labels on which the baseline had no word to answer with.

Tried and dropped: reading «stopped» from progress in the scorer's loop_logs rule as well. On these records it cut
three recorded fixes (v5 E01-E03) whose loop_logs list a CPU-load role that prints one TICK and spins by design. The
loop_logs rule is unchanged.

## 3. Reproducibility check (`bench/repro_states.py`, called by `repro_v3.py --same-boot`)

New: the unmodified run must show (1) every program process that run.sh starts and (2) every thread state the
label's `states` text names, on a thread of the scenario's own processes. Applied to the recorded AI-off runs:

| set | shows the label's situation | does not | cannot be told from the record |
|---|---|---|---|
| v4 (24) | 19 | 4: D08, D13, D20, D23 (label names a REPLY-blocked client; no program thread was in REPLY) | 1: D07 |
| v5 (12) | 10 | 1: E04 (run.sh starts 4 processes, 3 in the process list; no REPLY) | 1: E12 |
| v3 (21) | 14 | 0 | 7 (v3 records hold no pidin lines of an unjudged program) |

The five flagged scenarios are the ones the failure classification found by hand. «Cannot be told» is a limit of the
records (they keep the judged processes' lines only, and until today no line of a MUTEX/SEM/CONDVAR wait); the boot
that `repro_v3.py` makes has every line. The check is per scenario, not per role, and reads state words only.

## 4. Observer (`qnx_doctor/waitgraph.py`, `progress.py`)

- The pidin parser used for the «unknown» reason kept a Blocked column of one token only. In the recorded runs a
  MUTEX wait printed three (for example `(0x3f08248038) 204820-03 #0`), so those lines were dropped whole and the
  reason for v4 D02, D10 and D17 never mentioned a mutex. The column is now kept as text and every «unknown» reason
  lists the waits outside message passing as pidin printed them. Nothing is interpreted: whether the last value of
  such a line is the thread that holds the lock is **not** decided, mutex waits are not edges of the graph, and the
  three scenarios would still be answered `unknown`.
- A thread SEND-blocked on its own process, with no thread of that process RECEIVE-blocked in any snapshot (the
  shape of v4 D22), is now shown in the «unknown» reason the same way. It is **not** named: v4 D22 would still be
  answered `unknown`, and no detection number on this page changes. (A first version of 2026-11-21 named it a
  deadlock of one member; that was taken back the same day because it had never been checked on a target. Naming it
  waits for a new dev scenario checked on a target.)

Neither change alters what the tool names, so no detection number moves. Neither has been run on a target.
