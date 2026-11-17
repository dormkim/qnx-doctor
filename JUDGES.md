# For judges

This page says what qnx-doctor claims, where each number comes from, and what went wrong. Everything below can be
checked from files in this repository; the full test loop needs QNX SDP 8.0 and QEMU, which we cannot redistribute.

## The claim

qnx-doctor says when it cannot know why a QNX program stopped, and it does not claim a fix that a rerun on the target
did not prove.

It does **not** claim to fix more hangs than a careful baseline. On the one test set we did not write, it fixed as
many as a baseline given the same retry (3 of 8), raised one false alarm, and missed one deadlock the baselines found.

## The test that backs it: sealed set v3 (2026-11-17)

| step | what happened | where to check |
|---|---|---|
| Written | 21 QNX 8.0 scenarios and an answer key, by an agent that had not read our source, prompts, verifier or past results. What it did read is listed. | `bench/sealed_v3_1117/README.md` |
| Sealed | sha256 of the answer key and of the scenario tree, committed before any run (commit d9d562b). | `bench/sealed_v3_1117/SEAL.md` (the command to recompute both hashes is in it) |
| Rules fixed | Scoring rules for "unknown", multi-cause cases and exclusions, committed before the run (caecd37). | `bench/score_structure.py`, `tests/unit/test_score_v3.py` |
| Reproduced | Each unmodified scenario was run once without any doctor and compared with the answer key; disagreements were excluded with a reason, labels untouched (b075721). | `bench/sealed_v3_1117/excluded.json`, `repro_20261117.json` |
| Run | Once, four arms, same model. Not run again. | `results/sealed3_20261117/` (raw jsonl per arm, logs, score) |

Exclusions (5 of 21; 16 scored):
- q02, q06, q09, q21: our second observer never returned a second TICK count (it reads logs from the disk while
  these scenarios load the CPUs above the disk driver). All four are priority-chain cases, so this set tells nothing
  about priority chains.
- q16: a loop that should keep running printed nothing. Most likely our recorder bug (below).

Arms: **ours** (wait graph from `pidin` on the target, AI fix, up to 2 tries); **naive** (source and TICK logs only,
1 try); **naive_x2** (naive plus one retry with the rerun's result). All fixes go through the same rerun check.

Caveats before the table: one run; 16 scenarios; 8 fixable faults, 4 healthy, 4 "unknown". For "unknown", qnx-doctor
printed "loop not running but no wait cycle or chain found" (the literal "unknown" word came after v3) and did not
call the AI; the rule committed before the run scores that as "cannot tell".

| arm | kind found | deadlock | missing reply | healthy left alone | unknown said "cannot tell" | false alarm | fixed (rerun-proven) | "fixed" on an unknown case | false fix |
|---|---|---|---|---|---|---|---|---|---|
| ours | 13/16 | 4/5 | 3/3 | 3/4 | 3/4 | 1/4 | 3/8 | 0 | 0 |
| naive | 12/16 | 5/5 | 3/3 | 4/4 | 0/4 | 0/4 | 2/8 | 2 | 0 |
| naive_x2 | 11/16 | 4/5 | 3/3 | 4/4 | 0/4 | 0/4 | 3/8 | 3 | 0 |

The "fixed on an unknown case" column, read by a person: on q12 and q17 the cause is outside the given sources (a
signal from a supervisor and a semaphore from a calibration tool, neither in the scenario). Both baselines removed
the wait or posted the semaphore themselves; the loop ran again, so the rerun check passed. That is the case our
claim is about: a fix the program's evidence does not support. naive_x2's third one (q01, a name mismatch) can be
fixed from the source.

## What went wrong

- **Tie on fixes.** ours and naive_x2 fixed the same three scenarios (q08, q14, q15). On this set the wait graph and
  the QNX docs added nothing over a second try.
- **False alarm, q19.** A server holds each reply until a periodic pulse arrives, so every `pidin` snapshot shows a
  client REPLY-blocked on a server waiting in RECEIVE. That is what a missing reply looks like, and our judge decided
  from thread states alone. The client was still printing TICKs.
- **Missed deadlock, q10.** Most likely our harness, not the judge: `common/qd_trace.c`, the recorder we link into
  every scenario with `-Wl,--wrap`, made its own kernel calls between the program's `TimerTimeout()` and the real
  `MsgReceive`/`MsgSend`. `TimerTimeout()` applies to the next kernel call only, so the program's timeout was used
  up, it waited forever in an earlier receive, and the deadlock never formed. Evidence: the recorder logged no send
  attempt from either program; a baseline retry that removed that receive from the main thread made the loop run;
  and a new harness test (`tests/harness_checks/tt01`, not part of v3) shows loops with RECEIVE and SEND timeouts
  stuck with the current recorder and running with the fixed one. The baselines named this deadlock from the source.
- **q11 called healthy.** A CPU spin stopped the loop after it had printed some TICKs; the code treats "some TICKs"
  as running.
- **Harness bug that cost 4 scenarios.** The second observer starved on disk reads (see exclusions).

None of these fixes is measured on v3, and v3 will not be rerun. Since 2026-11-17 they are on `main`: the recorder
fix, the observer fix (a second TICK count from the same observer in the same boot, no second observer), the progress check (does the TICK count
grow?) and an explicit `unknown` output (no AI, no fix). They were checked only on new harness tests
(`tests/harness_checks/`) and unit tests. They will be measured on sealed set v4, written by a new author, sealed
before the run and run once: `bench/V4_PLAN.md`.

## Earlier numbers, and why they count for less

Before v3 we measured on sets we built ourselves: 7 hand-written scenarios (`tests/sealed_hang`) and two seeded
generators (`tests/gen_hang`, v1 20 and v2 30 held-out seeds). The same people wrote the generators, the verifier,
the baseline prompt and the scorer, and the verifier rule was changed once after looking at v1. On v2 every arm named
all 30 kinds, and ours fixed 24/25 on the first try against naive 20/25 (naive had one try). We report them as
development numbers: [docs/measure_structure_1116.md](docs/measure_structure_1116.md),
[docs/measure_holdout_1116.md](docs/measure_holdout_1116.md). None of those scenarios use `TimerTimeout`, so the
recorder bug does not touch them.

## Checking without QNX

- Unit tests (wait graph, structure check, scorer, verdicts): `python3 -m unittest discover tests/unit`.
- Read-only analysis of a recorded `pidin` capture: `python3 -m qnx_doctor.cli hang --pidin tests/unit/fixtures/pidin_dl2_1115.txt`.
- Re-score the recorded v3 run from its files: `python3 bench/score_structure.py results/sealed3_20261117/labels.json --exclude-file results/sealed3_20261117/excluded.json --fresh code=results/sealed3_20261117/code.jsonl ai=results/sealed3_20261117/ai.jsonl naive=results/sealed3_20261117/naive.jsonl naive_x2=results/sealed3_20261117/naive_x2.jsonl`.

Only states are published (blocked or running, TICK or no TICK). No QNX timing or performance numbers (QNX licence 4.6(i)).
