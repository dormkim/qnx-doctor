# Gates before sealed v6: what the dev checks showed (2026-11-22)

**Verdict: cannot freeze yet.** Gate 2a failed (one fake fix was accepted), the self-send check found the verifier
accepting a fake and rejecting the real fix, and reading the code for the run found four more blockers (section 7).
The mutex question is decided and fixed. Per-call usage is recorded and tested with fake responses.

Scope: steps 1 and 2 of `bench/V6_PLAN.md` section 4, preparation only. Dev pools, `tests/harness_checks/` and new
dev scenarios only. **No model or API call was made.** No v6 scenario was written, no sealed set was run again, no
recorded score table and no criterion of the plan's section 1 was changed. States only (QNX licence 4.6(i)): these
are checks of our own tool and harness, not statements about QNX.

Branch `v6/dev-gates-1122`, from main 8ac11ad:

| commit | what |
|---|---|
| 4111c5a | the dev checks (scenarios and `fake_fix_check.py --tick-first / --checks`) |
| 18dcf14 | the observer reads every thread; a mutex hang is never proven fixed |
| 85e8096 | `response.usage` per call |

Conditions: `QD_SMP=1` as in the plan, one QEMU at a time under the existing lock, a timeout on each boot, no AI.
"pre" = product code of 8ac11ad, "post" = 85e8096, each run twice.

## 1. Unit tests

| | with the SDK | without the SDK |
|---|---|---|
| start (8ac11ad) | 165 run, OK | 165 run, OK, 3 skipped |
| end (85e8096) | 183 run, OK, 0 network attempts (connect blocked and counted) | 183 run, OK, 10 skipped |

Of the 18 new tests, 9 of the 10 observer tests and 7 of the 8 usage tests failed or errored on the old code.

## 2. Check a: fake fixes, ring that prints a TICK before its first send. **FAILED**

Dev ring `s9370e5` with each member's TICK moved in front of its send. Same result in pre1, pre2, post1 and post2.

| fix | fixed | what rejected it (current rule) |
|---|---|---|
| real: pulse to the next member | yes | - |
| fake: run.sh rewired | no | static rule: `run.sh starts the processes (the wiring)` |
| fake: one member stops sending | no | `was not ticking any more at the second count of the rerun`; pair lost |
| fake: every member stops sending | no | `no stopped loop printed at least 2 more TICKs than before`; pairs lost |
| fake: more TICKs, same cycle | no | `still hung: DEADLOCK` |
| fake: one more TICK, then stopped | no | `no stopped loop printed at least 2 more TICKs than before` |
| fake: more TICKs, then stopped again | no | `was not ticking any more at the second count of the rerun` (only this rule caught it) |
| fake: TICKs go on, no message at all | no | `pair no longer exchanges messages` |
| **fake: TICKs go on, messages stop after a few rounds** | **yes, wrong** | nothing |

- The real fix passes, so the rule that reads the second count needs no loosening. That rule works: one fake is
  caught by it alone.
- The last fake passes because message pairs are counted once and need only `MIN_DONE` (2) exchanges, while TICKs
  are counted twice. A program that exchanges a few messages and then only ticks is reported fixed. This bears
  directly on criterion A.
- The fakes that existed before (dev pool ring and chain): 2 of 2 real fixed, 6 of 6 fake rejected, in all four rounds.
- A build failure or failed boot no longer counts as "fake rejected" in `fake_fix_check.py`. None happened.

Proposed, not implemented: count the message records twice in the same boot (next to TICKS and TICKS2) and require
each earlier pair to still grow. `qd_trace.c` writes its record only at small counts and powers of two, so the
recorder has to flush more often too. That is a harness change: every dev check has to be run again after it.

## 3. Check b: self-send

| scenario | judged (four rounds) | "SEND-blocked on itself, nobody receiving" found |
|---|---|---|
| `ss01`: no thread receives | `unknown (no_info)`, self-send shown | yes, in every snapshot |
| `ss02`: a second thread receives and replies | `none`, loop grew | no |
| `ss03` (extra): a receiver exists but waits on a semaphore | `unknown (blocked_other)`, SEM and self-send shown | yes, in every snapshot |

**Proposal: keep "shown, not named" for v6.**
1. The two requested scenarios are told apart, but `ss03` shows the same SEND state with another cause. The states
   alone would name it a deadlock wrongly.
2. Naming sends the case to the AI and the verifier, and the verifier is wrong on this shape:

| fix on `ss01` | should be | is (four rounds) |
|---|---|---|
| real: a second thread receives | fixed | **rejected** (`non-messaging process changed its threads' priority or load`) |
| fake: the send is deleted | rejected | **fixed** |

Cause: `structure.build` leaves out a pair of a process with itself, so a self-send is neither protected nor counts
as messaging. Our arm does not reach this (it answers `unknown`), but a baseline that names a deadlock would be
credited with the fake. Proposed, not implemented: count self pairs. Replayed in memory on the saved boots of pre1,
pre2 and post1, that gives real fixed and fake rejected in all three. It still needs tests and a target run.

## 4. Check c: MUTEX threads. **Reproduced, decided, fixed**

`mx01`: two threads, opposite lock order, no messages. `mx02`: a server with the same bug in its workers and a
REPLY-blocked client.

| | pre (two rounds) | every thread, nothing else (replay of both pre rounds) | post (two rounds) |
|---|---|---|---|
| mx01 threads in the first record | **1 of 3** | 3 of 3 | 3 of 3 |
| mx01 real: one lock order | rejected (thread count artifact) | rejected (busy flag changed) | rejected: cannot be proven |
| mx01 fake: one worker removed | rejected | rejected | rejected |
| mx01 fake: second lock deleted | rejected (same artifact) | **fixed, wrong** | rejected: cannot be proven |
| mx02 threads in the server's record | **1 of 4** | 4 of 4 | 4 of 4 |
| mx02 named | **`missing_reply`, wrong** | `unknown` | `unknown (blocked_other)`, MUTEX shown |
| mx02 real: one lock order | fixed | fixed | rejected: cannot be proven |
| mx02 fake: lock order + one worker removed | **fixed, wrong** | rejected | rejected |

Decision:
1. **Read every thread** (structure record, process count, judge). "No thread removed" and "all threads
   RECEIVE-blocked" were both false while MUTEX threads were invisible.
2. **Not that alone.** It makes deleting a lock pass as a fix. So if a thread waited on a mutex in every snapshot
   of the first observation, no fix is counted (`fix cannot be proven: ... lock use is not recorded`). This keeps
   what the plan already says (no arm can fix a mutex scenario), now with the true reason.

What this costs:
- The real fix of `mx02` is no longer counted. No mutex fix of any arm will be.
- A lost reply in a server with a helper thread in MUTEX, SEM or CONDVAR is now `unknown`, not `missing_reply`.
- A message hang next to a steady mutex wait cannot be proven fixed either.
- The scorer lists "cannot be proven" under "shortcut rejected". The v6 report has to say so.
- `hang --pidin` and `--live` still use the strict parse and can still give the `mx02` false name.
- A SEM or CONDVAR wait has no such "cannot be proven" rule.

Regression:
- Check a and the old pool fakes: the same rows before and after.
- Harness checks sp01, bo01, lp01, oc01, tt01: the same answers in four rounds.
- Dev v2 (`stability_check.py --n 1`, two rounds, missing reply as positive control): main and branch judge the
  saved boots identically. `t9273af` is still `missing_reply` and its real fix still passes.
- In that set `t5e594f` (labelled priority chain) does not build its situation, under main and branch alike: the
  client is gone, the answer is `unknown` and the fix is not proven. The generator still writes the id file
  through temp + rename, which our harness helper stopped doing on 2026-11-18 (likely cause in our harness, not
  tested separately). The real fixes of the other cases pass; the name-order edit stays hung, as recorded on
  2026-11-17, and the event shortcut is rejected.
- Recorded v3 to v5 judgments, looked at offline: none moves in the records that kept their lines.
  `rejudge_records.py` prints the same as on main. `rejudge_records.py --fake` was not run.
- Prompts of all arms: byte for byte as on main.

## 5. Agreement between the two runs

| pair | rows | different verdict | different state (progress, kind, reason class) |
|---|---|---|---|
| pre1 / pre2 | 32 + 5 harness checks | 0 | 0 |
| post1 / post2 | 32 + 5 harness checks | 0 | 0 |
| dev v2, round 1 / 2 | 17 | 0 | 0 |

No boot failed and none was repeated. Two runs show no wobble here; they are not proof of stability.

## 6. Usage per call

`ai.usage_record` runs right after each response, before the reply is parsed. It keeps model, stop reason, input,
output, cache and thinking tokens; a missing count is null, not 0. Where it goes:
- our arm: timeline entries `kind: usage`;
- baselines: the row's `usage` list;
- both: a `qd-usage {...}` line on stderr at once, so a case that crashes still leaves its earlier calls in the log.

Tested with fake clients that return the SDK's own response type. Never tested against the API.

## 7. Freeze: no

| # | blocker | evidence | to clear it |
|---|---|---|---|
| 1 | a fake is accepted on the ring | section 2, four rounds | second message count, then all checks again |
| 2 | self-send: fake accepted, real fix rejected | section 3, four rounds | count self pairs, test, target run |
| 3 | **the AI's "read-only" probe can run any command** | dummy-value test: `find . -maxdepth 0 -exec env ;` passed the confined probe and printed a dummy `ANTHROPIC_API_KEY`; `-exec sh -c` ran | refuse find's action options and paths inside options, exact program names, no `ANTHROPIC_*` in child environments |
| 4 | **an edit can read files outside the work copy** | dummy-file test: an absolute `#include` was not rejected, and the file's text reached the build error that our retry is given | refuse absolute and `..` includes (and other file-embedding directives), cut quoted lines from build errors |
| 5 | `run_sealed3.sh` does not run the planned v6 | no `--allow-unknown`, no `QD_SMP=1`; `wait $A $B $C` sees only the last arm's exit status, so a failed arm still ends "done"; it always runs the main checkout | a v6 mode that sets both, fail if any arm fails, run from the freeze commit |
| 6 | scorer, criterion C | a baseline word outside the vocabulary (`livelock`) is flagged as an error by the reader and still scored as a hit on an `unknown` label | hit only on the word `unknown`, unit test |

3 and 4 mean that the answer key and the API key are not protected from the model during a run, and that the README
sentence "The AI never runs a command that changes the system" is not true today. The 5 probe entries in the
committed jsonl run records (`results/`, `bench/`) use none of these options. A search of the tree and history for Anthropic key-shaped strings
found none. Not checked: uncommitted logs and other kinds of secret.

Also before the freeze: README and JUDGES wording that claims more than 1 to 4 allow, and the 2-call reply check of
the plan's section 2 (not done, needs the user's OK).

## 8. Key and account path (code and variable names only; no value or env file was opened)

- `bench/run_sealed3.sh` sources `~/.config/qnx-doctor/env` with auto-export. All arms then call `Anthropic()` with
  no arguments (`qnx_doctor/ai.py`, `bench/naive_hang.py`). Model: `QD_MODEL`, default `claude-opus-5-5`.
- SDK 2.8.0 takes, first match wins: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_PROFILE`, workload
  identity variables, then a profile saved on disk. `ANTHROPIC_BASE_URL` and `ANTHROPIC_CUSTOM_HEADERS` apply too.
- So which account pays **cannot be told from the code**. Anything the file does not set comes from the calling
  shell, and a missing key falls through to a saved profile without stopping. For v6: a clean environment, stop
  if `ANTHROPIC_API_KEY` is empty, and the user confirms which organisation owns that key.

## 9. What needs the user's OK

Price as in the plan ($4 / $20 per million tokens); the live page was not checked. Tokens are still assumptions.

| item | calls | amount |
|---|---|---|
| reply check, sp01 and bo01 | 2 | cents |
| v6, expected (plan) | about 140 | about $20 |
| the plan's "upper bound" | 378 | about $60, **not a cap** |
| what the code allows | 570 (any of the 30 can reach the AI: 30 x 16 + 30 + 60) | about $91 at the plan's tokens per call |

The last line is not a money cap either: input grows with each turn of a conversation, the code has no budget stop,
and the SDK retries failed requests. The sources sent per scenario were about 20,000 characters on three dev
scenarios. The OK has to name the amount, what happens if it is passed, and the key's account.

## 10. How to repeat, and what was not run

```sh
python3 tests/gen_hang/gen.py --pool dev --out runs/dev
QD_SMP=1 python3 bench/fake_fix_check.py --pool runs/dev --tick-first --out runs/tick_first.jsonl
QD_SMP=1 python3 bench/fake_fix_check.py --pool runs/dev --out runs/pool.jsonl
QD_SMP=1 python3 bench/fake_fix_check.py --pool tests/harness_checks --checks ss01,ss02,ss03,mx01,mx02 --out runs/checks.jsonl
python3 -m unittest discover tests/unit
```

175 boots in total. Raw outputs stay in the untracked `runs/gates_1122/` of the worktree.

Not run: any model call (including the 2-call check), the seal, the reproducibility check, v6, two-core boots,
`--live`, `hang_demo`, and `rejudge_records.py --fake`. Not implemented: every "to clear it" in section 7.
