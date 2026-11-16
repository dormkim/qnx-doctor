# Hang doctor: first run on the sealed and held-out sets (2026-11-16)

Sets: `tests/sealed_hang` D01–D07 (hand-written, sealed ec5ac0e) and the held-out random pool (20 seeds, sealed d7520a3,
generator v1). Both were run for the first time today, once. Held-out labels were checked by hash only before the run:
they are identical to the sealing commit.
States only: hung or running, TICK or none. No QNX timing or performance numbers (QNX licence 4.6(i)).

## Arms
- **Code only (AI off)**: the `pidin` snapshot on the target goes into the wait graph, and the code names the kind. No fix.
- **AI on**: the same graph, plus source and QNX docs. The fix comes back as `edit_file` actions. Code applies it to a copy, rebuilds with `qcc`, boots, and reruns. Up to 2 attempts.
- **Naive baseline** (`bench/naive_hang.py`): the same model, one reply, given only the source and the TICK logs. No `pidin`, no graph, no docs, no probes. Its fix goes through the same rerun check.

## Before the run (dev pool only; held-out not looked at)
- The 2 dev misses (seeds 1003, 1017) were a fault of our harness. Our observer was loaded from the disk image (`/var`, `/tmp`) after the scenario had started, and the scenario's own CPU load, set above the disk driver's priority, kept our observer from loading until the load ended, so our snapshot showed a system that had already recovered. Fix: start `snap` before the scenario and wake it with the builtin `kill` (8f013bd).
- Dev seed 1014: at the snapshot instant the observer itself held both CPUs, so the hog threads showed READY instead of RUNNING. Chain rule: a middle-priority thread that is RUNNING **or READY** (12912b8).
- Dev after both fixes, code only: deadlock 10/10, priority chain 7/7, healthy 3/3, false alarms 0.
- Verifier tightened before the run (5649f03): every 0-TICK log must tick again, and no program process may disappear.

## Results as run

| set | arm | deadlock found | chain found | healthy found | false alarm | fixed (rerun) | false fix | AI cause label ok |
|---|---|---|---|---|---|---|---|---|
| sealed 7 | code only | 4/4 | 1/1 | 2/2 | 0/2 | - | 0 | - |
| sealed 7 | AI on | 4/4 | 1/1 | 2/2 | 0/2 | 2/5 | 0 | 2/2 |
| sealed 7 | naive | 4/4 | 1/1 | 2/2 | 0/2 | 2/5 | 0 | - |
| held-out 20 | code only | 12/12 | 1/1 | 7/7 | 0/7 | - | 0 | - |
| held-out 20 | AI on | 12/12 | 1/1 | 7/7 | 0/7 | **13/13** | 0 | 13/13 |
| held-out 20 | naive | 12/12 | 1/1 | 7/7 | 0/7 | 12/13 | 0 | - |

Every proven AI fix also named a culprit line that exists in the source (`culprit_in_source`).

## Verifier flaw found by the run (reported separately, after the fact)
On D03, D04 and D05, both arms removed the cycle or chain, and the stopped client ticked again. The fix was still rejected,
because those scenarios have server and logger logs that never print TICK by design, and the new rule required every
0-TICK log to tick. Corrected rule (bb92701): at least one stopped loop ticks again, no loop that was ticking stops,
and no process is gone. `bench/replay_fix.py` re-applied **the same recorded edits** (no new AI call) and judged them
with the corrected rule:

| set | arm | fixed, as run | fixed, re-judged (post-hoc) |
|---|---|---|---|
| sealed 7 | AI on | 2/5 | 5/5 |
| sealed 7 | naive | 2/5 | 5/5 |
| held-out 20 | naive | 12/13 | 12/13 (s5b174f still fails) |

The re-judged column uses a rule changed after seeing these results. A clean number for it needs a new sealed set.

## Baseline vs ours: what differs
- **Naming the kind is not where we win on these sets.** The baseline read the source and got every kind right, with 0 false alarms. These scenarios are small, and the cause can be read from the code.
- **How the hang is removed differs.** 7 of the baseline's 12 held-out fixes edit `run.sh`. They rewire who talks to whom, or start one ring member in a mode where it no longer sends. One example (s7628ec): `if (!rf) qd_send(...)`, which makes a member stop sending. Liveness passes, but the program no longer does what it did. None of our 13 fixes touch `run.sh`. They stay in the C source and use the QNX idiom: `MsgSendPulse` instead of a synchronous send back, reply first, or inheriting the client's priority.
- Our verifier accepted those rewiring fixes too, because it checks liveness only. Next step: a «same message topology» check, meaning the same process pairs still exchange messages and `run.sh` is unchanged. Then measure it on a new sealed set.

## Caveats
- Held-out has only one priority chain (the kind draw is random). The chain result rests on 1 held-out case + 1 sealed case + 7 dev cases.
- AI ran once (not twice for variation).
- Hand-written sealed files have names that hint at the bug (`pingpong.c`, `cb.c`, `prio.c`). Comments are stripped, but names are not.

Raw runs on the server: `runs/ho_1116/` (jsonl per arm, `score.md`, replay files). Scored with `bench/score_hang.py`.
