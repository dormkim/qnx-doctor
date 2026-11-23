# For judges

This page says what qnx-doctor claims, where each number comes from, and what went wrong. Everything below can be
checked from files in this repository; the full test loop needs QNX SDP 8.0 and QEMU, which we cannot redistribute.

## The claim

`qnx-doctor verify` stops most patches that only make a hung QNX program run again, without reading the patch's
intent: on 55 patches nobody on our side wrote, it accepted 5 of 30 bad patches where a "does it run again" check
accepted 19, and no forgery. It also rejected 4 of 17 genuine fixes, and it cannot tell what a reply means. The
diagnosis (`hang`) is not claimed to beat the model alone: on sealed set v6 it did not.

## The test that counts for the gate: patch set v7 (2026-11-23)

| step | what happened | where to check |
|---|---|---|
| Planned | Classes, checkers, criteria G1 to G4 and the wording rules, before any v7 code | `bench/V7_VERIFY_PLAN.md` |
| Frozen | Gate, judge, structure rules, scorer; re-frozen once for a loader-only fix | `bench/FREEZE_V7.md`, tags `v7-freeze`, `v7.1-freeze` |
| Written | 55 patches by a fresh agent in a plain folder with only the 14 programs, the harness and the brief | `bench/sealed_v7_1123/README_author.md` |
| Labelled | By the author and by a second fresh reader who saw neither the author's labels nor the run; 53 of 55 agree | `labels_author.json`, `labels_reader.json` |
| Sealed | sha256 of the patches and the author's labels before the run | `bench/sealed_v7_1123/SEAL.md`, tag `v7-seal` |
| Run | Once (a first run that failed in the loader is kept) | `run_1123b/`, `run_1123_loaderbug/` |
| Scored | By the scorer committed before the seal | `bench/score_verify.py`, `run_1123b/score.md` |

Outcome by the criteria fixed in advance: G1 met (5 vs 19 bad patches accepted), G2 not met (4 genuine fixes
rejected, 2 allowed), G3 0 forgeries accepted, G4 the v7 review rule caught 1 more masking patch than the v6 gate and
cost no genuine fix. [bench/sealed_v7_1123/RESULT.md](bench/sealed_v7_1123/RESULT.md).

What "prove" means, and where it was weaker than it read (found on 2026-11-22, `bench/V6_GATES_1122.md`):

- The rerun shows the stopped loop ticking and the same process pairs still exchanging messages. It is not a proof
  that the program is correct, and it is not tamper-proof: on a dev target a fix that forged its own message record
  passed. For v6, every edit counted as fixed is read in full before the result is reported.
- Raising a starved server's priority without fixing its channel passes. v6 accepts it as a fix and also reports
  those fixes as a separate count.
- Until 2026-11-22 messages were counted once. Fake fixes that exchanged a few messages and then only ticked passed
  on dev targets. The "fixed" numbers of v3, v4 and v5 were recorded under that rule. The records cannot show whether
  any of those fixes stopped exchanging later in its run.
- "False fix 0" counts fixes on healthy programs. No arm has a fixed row on a healthy label in those records, and a
  verifier that was too lax cannot have hidden one. It does not say that every fix on a hung program was genuine.
- Until 2026-11-22 the AI's look-around commands could run other programs and a proposed edit could read other files.
  Nothing of that kind is in the recorded look-around commands or edits of v3, v4 and v5.

It does **not** claim to diagnose or fix better than the model alone. On sealed set v6 (30 scenarios, run once
2026-11-23) no arm reported an unproven fix (0, 0 and 0); a baseline allowed to say "unknown" matched the tool on the
5 unknown labels; qnx-doctor raised 3 false alarms on 7 healthy programs where the baselines raised none; it found 22
causes of 30 against 26 and 25, and fixed 11 hangs of 18 against 12 and 14. Every fix counted as fixed was read in
full; the check let one masking fix through in every arm. All of it: [bench/sealed_v6_1123/RESULT.md](bench/sealed_v6_1123/RESULT.md).

## The test that counts: sealed set v6 (2026-11-23)

| step | what happened | where to check |
|---|---|---|
| Frozen | Judge, verifier, scorer, prompts, harness and cost cap, with sha256 of each file | `bench/FREEZE_V6.md`, tag `v6-freeze` |
| Written | 30 scenarios and an answer key by a fresh agent in a sparse worktree holding only the harness, one example and the run script | `bench/sealed_v6_1123/README.md` |
| Sealed | sha256 of the key and the scenario tree, before any run | `bench/sealed_v6_1123/SEAL.md`, tag `v6-seal` |
| Reproduced | 30 of 30 agree on TICK expectations and thread states without the tool | `bench/sealed_v6_1123/repro_v6.json` |
| Run | Once, four arms, same model, 96 requests under a 40 USD cap | `bench/sealed_v6_1123/run_1123/` |
| Read | Every fix counted as fixed, by a reviewer who took no part in the runs | `bench/sealed_v6_1123/fix_review.jsonl` |

## Earlier: sealed set v3 (2026-11-17), now a development set

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
(`tests/harness_checks/`) and unit tests. They were measured on sealed sets v4 and v5 (run once each on 2026-11-18:
`bench/sealed_v4_1117/RESULT_1118.md`, `bench/sealed_v5_1118/RESULT_1118.md`). Corrected 2026-11-21: v3, v4 and v5 have
since been read case by case and are now used as development sets (`bench/DEVSET_RECALC_1121.md`); the number that
counts is sealed set v6, above.

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
