# Sealed v3 failure analysis: false alarm on a healthy scenario (q19), missed deadlock (q10) (2026-11-17)

Translated on 2026-11-23 from the Korean working note `docs/분석_sealed3_1117.md`, which is kept unchanged beside it because sealed files cite it by name. This English text is the version we submit.

What was read: `runs/sealed3_20261117/` (score.md, excluded.json, labels.json, and the jsonl and log files of the four arms),
`bench/sealed_v3_1117/` (README, SEAL.md, repro_20261117.json), the scenario sources q10, q13, q16 and q19,
`qnx_doctor/{hangdoctor,hang,waitgraph,structure}.py`, `tests/sealed_hang/common/{qd_trace.c,snap.c,check.sh}`.
v3 was **only read**. The v3 scenarios were not run again and not scored again.

## 0. Rules of this document (kept until v4)

1. The v3 score stays exactly as in `runs/sealed3_20261117/score.md`. v3 is not run again with the code fixes below, and we do not write «improved on v3».
2. The effect of the fixes below is measured **only on a new sealed set, v4**. v4 is written by a new author who has not seen the code, the v3 results or this document. The answer hashes are committed before the run, and the run happens once.
3. The harness fixes (H1 to H3 in section 5) go in **before** the v4 seal. If the harness is changed after the seal, that fact and the reason are written in the result document.
4. Fixes are tested only with the dev pool and `tests/harness_checks/` (tests of the harness itself).

## 1. Result re-checked (copied from score.md)

16 of 21 used. 5 excluded (labels not changed): q02, q06, q09 and q21 because the second observer did not come back, q16 because «a loop that must keep running showed 0 TICK».

| arm | kind found | deadlock | no reply | healthy | unknown | false alarm | fixed (retries included) | «fix» on unknown |
|---|---|---|---|---|---|---|---|---|
| code / ai (ours) | 13/16 | 4/5 | 3/3 | 3/4 | 3/4 | 1/4 | ai 3/8 | 0 |
| naive | 12/16 | 5/5 | 3/3 | 4/4 | 0/4 | 0/4 | 2/8 | 2 |
| naive_x2 | 11/16 | 4/5 | 3/3 | 4/4 | 0/4 | 0/4 | 3/8 | 3 |

- Scenarios fixed: ai = q08, q14, q15. naive_x2 = q08, q14, q15 (the same three). naive = q08, q15. False fixes are 0 in all four arms.
- Why the priority chain column is 0/0: the 4 excluded scenarios (q02, q06, q09, q21) are **all of the chain labels**. v3 says nothing about chains.
- Our «unknown» 3/4 does not come from the tool printing the word `unknown`. The code prints «the loop stopped but no cycle or chain was found» (`loop not running but no wait cycle or chain found`), and the scorer reads that sentence as unknown (the rule in commit caecd37, committed before the run). In this case the AI is not called at all, so the fix count is 0. It is not «the AI judged and stopped».
- The axes where we were wrong: misleading_comment and timeout_misuse (both q10), cpu_spin (q11).

## 2. False alarm on a healthy scenario = q19 (`ok_longpoll`)

Label: dash is REPLY-blocked on evbus, and evbus holds an rcvid and is RECEIVE-blocked (the same picture as a missing reply). But a pulse every 300 ms releases the reply, so dash keeps running. Correct answer: `none`.

Our verdict: `missing_reply`. Evidence (code.jsonl q19):
- The dash TICK in the snapshot = 13. The repro check record (`repro_20261117.json`) has 13, then 27 a moment later. So the loop was running.
- The judge (`waitgraph.judge`) looks only at thread states. If the same pair «dash → evbus, all evbus threads RECEIVE» shows up in three pidin captures (PIDIN, PIDIN2, PIDIN3), it counts as a missing reply (`_persists`). Dash sends again as soon as it gets a reply, so all three captures show the same picture.
- `healthy` in `hang.observe` is `judge == none and TICK sum > 0`. If the judge names anything, it is recorded as «stopped» even when TICK is 13 (`loop stopped` in the timeline).

Root cause: **it judges from state alone and does not look at progress (did TICK grow?).** The three-capture persistence rule was added to filter out «passing states» (11/17), but it cannot filter healthy cases that always look like the same state (long polling, delayed replies).

Another failure with the same root: **q11** (cpu_spin, correct answer unknown). uplink printed 6 TICK and stopped. The judge found no cycle, chain or missing reply, and because the TICK sum was 6 > 0 it ended with «healthy (no hang found)». This also happened because it did not check «is TICK growing now?». In q19 TICK was growing and it said stopped. In q11 it had stopped and it said healthy.

## 3. Missed deadlock = q10 (`sendtimeout`)

Label: navcore asks routemap for a route (only a send timeout is set) and is REPLY-blocked. Before replying, routemap synchronously asks navcore for its position, with a 300 ms timeout, and retries forever. Correct answer: `deadlock`.

Our verdict: `none` («loop stopped, no cycle or chain»). The other three arms ran to the same result (the re-run graph was `no wait cycle and no priority chain` for all). The two baselines **read the source** and named it deadlock.

Root cause (likely, with the 3 pieces of evidence below): **`qd_trace.c` in our harness swallowed the scenario's kernel timeout.**
- `TimerTimeout()` sets a timeout on **only the next single kernel call** (QNX documentation). The wrapper functions in `qd_trace.c` make their own kernel calls before the real `MsgSend` / `MsgReceive`: `ConnectServerInfo` (to find the peer pid), and, when the count is small or a power of 2, `open` / `write` on `/dev/shmem/qdm.<pid>`.
- So navcore's startup `serve_for` (TimerTimeout RECEIVE 1.5 seconds, then MsgReceive) ended up receiving forever without a timeout. navcore never sent the route request, and routemap waits in receive. Both are in RECEIVE: no cycle and no TICK. The deadlock the label describes never actually formed.

Evidence:
1. Message structure in code.jsonl q10: `pairs: {}`, `receivers: [navcore, routemap]`. `qd_trace` records a MsgSend **even when it is only attempted** (att, written to the file on the first call). An empty pairs set means neither program ever tried to send an application message. By the label, there should be a navcore → routemap attempt.
2. The first fix of naive_x2 (q10) took `serve_for` out of the navcore main thread (the startup phase went to a thread, and the loop body used `usleep`). On re-run it got navcore TICK 20 (rejected because it changes the structure). This means it runs once the timed receive is removed from the main thread.
3. Harness test `tests/harness_checks/tt01` (not v3; newly written for this analysis): a loop that repeats `TimerTimeout(RECEIVE 100 ms)` + `MsgReceive` on a channel nobody sends to. With `qd_trace.c` from main, TICK is 0 (the timeout does not take effect). With the fixed `qd_trace.c` (branch `fix/trace-timertimeout`), TICK keeps coming. The result is in the table in section 5.

Limit: the raw pidin text of the first snapshot was not kept. `hang.observe` keeps in the timeline only the lines of the pids the judge named, and when the judge says none, that is 0 lines. So «both RECEIVE» cannot be shown directly from raw text, and it is inferred from 1 to 3 above.

Other v3 scenarios this bug touched (only q10, q13 and q16 use TimerTimeout, by `grep`):
- **q16** (healthy, excluded): the exclusion reason was written as «early timer», but east and west showing 0 TICK is probably the same cause (it uses `serve_for` and `TimerTimeout(SEND|REPLY)`).
- **q13** (deadlock + missing reply, accept_kinds has missing_reply): if pumpctl's `serve_for` receives forever in the same way, pumpctl stops after its first TICK without a cycle. We got missing_reply (on the alarmd side) right, but the fix condition is «both loops resume», so it may have been a **state no arm could fix**.
- So of the 8 in the «fixed /8» denominator, q10 and q13 may have run differently from the source because of the harness. It hits all four arms equally, so the «tie» does not change. The score is not corrected.
- The earlier sets (`tests/sealed_hang` D01 to D07, `tests/gen_hang` v1 and v2, `scenarios/`) do not use TimerTimeout (`grep`). This bug does not change the v1 and v2 numbers.

## 4. Harness problem: the second observer (4 excluded)

q02, q06, q09 and q21 dropped out at the repro check step with «TICK 15 to 37 at snapshot time, the second count could not be taken». The second observer (the snap that `bench/repro_v3.py` uses, started before the scenario and woken by a timer) starved while reading the `/tmp` (disk) log. The chain scenarios put a CPU load higher than the disk driver (devb-eide, priority 21), so disk reads are blocked. Two tries gave the same result.

Impact: all 4 chain labels dropped out, so v3 has no chain result. And the real arms also see only one TICK count from the first snapshot (the same root as section 2).

## 5. Fix candidates

| # | What | Failure it fixes | Status |
|---|---|---|---|
| H1 | `qd_trace.c`: remember per thread the last argument of `TimerTimeout` / `TimerTimeout_r` / `timer_timeout`, and re-arm it right before the real call in the wrapper (add the three functions to TRACE_CALLS in `hang.py`). Remaining gap: a program that sets a timeout and then makes another kernel call that is not wrapped would, unlike QNX, keep the timeout alive (no such scenario now) | q10, q13, q16 (presumed) | **merged into main** (11/17), confirmed with tt01 (below) |
| H2 | Count TICK in RAM: `qd_tick` also writes the count to `/dev/shmem`, and snap counts after the first snapshot and after PIDIN3. The second observer of the repro check also reads this count (does not touch the disk) | the 4 excluded (observer), the basis of the progress judgment in section 2 | **implemented** (11/17), the method changed: snap counts TICK twice in the same boot (`TICKS2`), and the repro check uses these two counts instead of the second observer (`repro_v3.py --same-boot`). `/tmp` is also a RAM link (`check.sh`). Confirmed with oc01 (section 8) |
| H3 | Always keep the raw judge text: `pidin_lines` covers all scenario processes, not only the pids the judge named (also when the verdict is none) | analyses like q10 staying at a presumption | **implemented** (11/17): when the verdict is none, the lines of all programs |
| J1 | Progress judgment: if a loop's TICK grew in the same boot, its wait is not counted as a missing reply or chain but as «slow, healthy». If TICK is above 0 but did not grow, it is seen as «stopped» and passed to the judge (today `>0` means healthy) | q19 false alarm, q11 miss | **implemented** (11/17): `qnx_doctor/progress.py`, `waitgraph.judge(moving=)`. Confirmed with lp01 and sp01 (section 8) |
| J2 | «Unknown» as an output word: today the scorer reads a note sentence as unknown. Print `unknown` («not explained by message waits, not enough information») explicitly in the tool output, and add one line on what more is needed (for example, the process state is SIGWAITINFO, SEM or NANOSLEEP) | match the claim in the public text to the output | **implemented** (11/17): `detected: unknown` + reason (spinning / blocked_other / no_info), no AI, no fix. The scorer reads the old note and the new word as unknown in the same way |
| J3 | The q10 shape (one side of the deadlock ring keeps waking up through timeout retries): if the snapshot still misses the cycle after H1, then when «A REPLY→B, B SEND→A» is seen in any one of the three captures, raise it as a deadlock candidate and confirm it with the TICK progress (J1) | the q10 shape | not implemented, check on dev first after H1 |

## 6. H1 check result (tests/harness_checks/tt01, not v3)

`bench/harness_check.py` booted once each and counted only TICK (QNX time numbers are not written).

| qd_trace.c | waiter (RECEIVE timeout) | cli (SEND timeout) |
|---|---|---|
| main (before the fix) | TICK 0 | TICK 0 |
| `fix/trace-timertimeout` | TICK keeps growing (29) | TICK keeps growing (29) |

The cli side is the third version. The first two had a wrong test design and gave 0 even after the fix (waiter went 0 → growing both times). Version 1 put a SEND|REPLY timeout on a named server: a `name_attach` channel has `_NTO_CHF_UNBLOCK` turned on, so a REPLY-blocked client is released only when the server replies (understood as QNX behavior, not the harness's fault). In version 2 the server accepted only the connect and then stopped, and in the snapshot cli stayed REPLY-blocked on the server (it seems the connect detection did not fit, not confirmed). Version 3 puts only a SEND timeout on a raw channel from `ChannelCreate(0)` plus a side-channel `ConnectAttach`. 85 unit tests pass (on the branch).

## 7. To do before v4

1. Merge H1 into main, add H2 and H3, then confirm only with the dev pool and tt01.
2. Add J1 and J2 after confirming «0 false alarms on healthy controls, existing dev verdicts kept» on dev.
3. Give v4 to a new author (someone who has not seen the code, the v3 results or this document). So that the chain labels do not drop out as a whole because of the harness, run the pre-seal repro check with the harness that has H2.
4. The v4 result document keeps the v3 score next to it, and also lists «what changed since v3» (those of H1 to J3 that went in).

## 8. Check after the fixes (11/17, not v3: only new harness tests and unit tests)

v3 was not run again or scored again. Everything below is `tests/harness_checks/` (scenarios newly written for this analysis) and unit tests. Each scenario was booted once (one QEMU at a time).

| test | what it looks at | state only (`state_only`) | fixed verdict |
|---|---|---|---|
| lp01 | a slow server that replies on each pulse (q19 shape, code newly written) | missing_reply | TICK grew → `none` (healthy) |
| sp01 | a loop that spins on the CPU after a few turns (q11 shape) | none (formerly «healthy») | `unknown (spinning)` |
| bo01 | waits on a semaphore nobody posts after a few turns | none | `unknown (blocked_other)`, SEM state by name |
| oc01 | priority chain under a CPU load higher than the disk driver | priority_chain | `priority_chain` kept |
| oc01 `--twice` | the second count of the repro check | v3 method (second observer): no count | same-boot method (`--same-boot`): there is a count |
| tt01 | is the TimerTimeout re-arm (H1) still the same after the merge | none | `none`, both loops grew |

One thing learned (correction to section 4): the explanation in section 4 that the second observer «starved reading the `/tmp` disk» was only half right. Even after `/tmp` was moved to RAM, in oc01 the second observer woke up, counted TICK, and then stopped in the `fork`ed child (pidin). It was the same when the observer executable was put in the boot image (RAM), and when `mlockall` was applied. The cause was not confirmed (presumed to be something waiting for the disk driver). So instead of fixing the second observer, we stop using it: the first observer counts TICK twice in the same boot (`TICKS2`), and the repro check reads those two counts. The first observer is the path every arm really uses, so the repro check now measures the same thing the arms see.

Unit tests 85 → 105, all pass. The scorer reads the old output (`none` + «loop not running…») and the new output (`unknown`) in the same way as unknown (confirmed by a test, not confirmed with v3 files). Of the findings from the independent review (a new agent, code only), two were fixed: the spinning reason could point at the CPU load program first, and the mixing when `--same-boot` and `--retry-missing` are given together. The two remaining risks are written in the limits of `bench/V4_PLAN.md` (a healthy loop with a long TICK interval can become «unknown», and two copies of the same program share a log).

J3 (the q10 shape, «a deadlock where one side keeps waking up through timeout retries») was not added. Whether the cycle is caught in the snapshot after H1 is looked at in v4.
