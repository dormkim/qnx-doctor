# Gates before sealed v6: what the dev checks showed (2026-11-22)

**Verdict (updated the same day, section 11): the six blockers of section 7 are repaired on the branch and
checked twice on dev targets. Do not freeze until the user has decided the points in 11.8.** Two fake-fix shapes
outside the six still pass (shown on a target, 11.6), and a rule cannot change after the seal.

Sections 1 to 10 are the record of the first pass (code up to 85e8096) and are left as they were found. Where section
11 says otherwise, section 11 is current.

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

## 11. Second pass: the six blockers repaired (2026-11-22)

Same limits as above: no model or API call, nothing pushed, merged or published, no sealed set written or run, the
plan's section 1 untouched, main still 8ac11ad. Attacks used dummy values and temporary files only.

| commit | what |
|---|---|
| 365d120 | blockers 3 and 4: probes, edits, child environments, sandbox |
| 0c43e1a | blockers 5 and 6: runner, scorer |
| 4fa7fbd | children end with their parent (found while testing) |
| 74fe632 | blockers 1 and 2: messages counted twice, self pairs |
| aa4feb4 | the one regression that this caused, narrowed |

### 11.1 Tests written first

| tests | failed on the code before the fix |
|---|---|
| `test_security.py` | 38 of the first 42 |
| `test_runner.py`, `test_score_vocab.py` | 11 of 12 |
| `test_orphans.py` | 1 of 2 |
| `test_recount.py` | 10 of the first 14; then 1 for the narrowed rule |

One old test was changed on purpose: it expected compiler text to be returned to the model.

### 11.2 Security: what is blocked

| attack | now | how it was checked |
|---|---|---|
| `find -exec/-execdir/-ok/-delete/-fprint*`, `file -C/-m/-z`, `grep -f`, `-L` and `-R` | refused: options are an allow-list per command | unit, and the reported exploits again |
| `./cat`, `/any/dir/cat`, a `cat` earlier in PATH | refused or not used: fixed absolute programs | same |
| paths by option, `..`, symlink, after `--`; unconfined probe outside work, SDP and QEMU | refused by realpath, and denied by the sandbox if the argument check is bypassed | unit, with the check switched off too |
| key in a child's environment; `set_env X=$ANTHROPIC_API_KEY` | gone: allow-list environment, expansion from the child's environment only | unit with a dummy key |
| `#include` by absolute path, `..`, macro, splice, trigraph, digraph; `#embed`, `#line`, `.incbin`; split over two edits | refused by the text check (first layer) | unit |
| the same with the text check bypassed, including token-pasted `asm` + `.incbin` | 15 of 15 combinations: no marker in the log, in the program or back to the model | real qcc; positive control: all three forms do embed a file that is inside the work copy |
| compiler text returned to the model | file and line numbers only | unit, real qcc |
| socket, io_uring, ptrace, keyrings | denied in the sandbox | unit for sockets; the filter lists the rest |
| no sandbox on the host | nothing runs (fail closed) | unit |

The whole arm was also run on the dev demo with a fake client (real build, boot and verdict): see 11.4.

### 11.3 Security: what is not blocked

1. `/tmp` and the licence directory during a compile are **watched, not denied**: qcc needs both and ignores TMPDIR.
   A foreign open fails the build and drops its output before any boot. Keep the v6 author worktree, pool and
   answers out of `/tmp` all the same (the plan puts the author worktree there).
2. The image step may use both directories unwatched. It gets built files as data, under names that code chose.
3. Build/boot doctor (not used by v6): a fix can execute code in the sandboxed re-run. It can still stat outside
   paths, chmod the user's own files and signal the user's own processes. Licence access is given only to a plain qcc
   call, so fixes of `make`-style commands that need qcc will now often stay unproven.
4. Everything inside the directory given to `qnx-doctor run` can reach the model, a `.env` there included.
5. `//` comments and `run.sh` comments reach every arm (only block comments are stripped). Tell the v6 author.
6. The guest is trusted: see 11.6. Kernel and QEMU bugs are out of reach.
7. Requirements grew: Linux x86_64, Landlock ABI 3+ (kernel 6.2+), strace.

### 11.4 Dev checks, every one twice on aa4feb4

Two rounds (fin3, fin4 in the worktree's untracked runs), and the two rounds before the judge fix for comparison:

| check | old judge, new fakes (two rounds) | now, round 1 | now, round 2 |
|---|---|---|---|
| a. ring that ticks first: real fixes | 3 of 3 fixed | 3 of 3 | 3 of 3 |
| a. ring that ticks first: fakes rejected | 7 of 10 (stop after a few rounds, stop after a burst, pulses nobody reads passed) | 10 of 10 | 10 of 10 |
| old dev pool, chain: fakes rejected | 3 of 4 (client's messages stop after a few rounds passed) | 4 of 4 | 4 of 4 |
| old dev pool, ring and chain: real / fake | not run as a whole | 2 of 2 / 7 of 7 | 2 of 2 / 7 of 7 |
| b. self-send, real fix | rejected | fixed | fixed |
| b. self-send, fakes rejected | 1 of 3 (send deleted, pulse nobody reads passed) | 3 of 3 | 3 of 3 |
| b. judged | ss01 unknown, ss02 none, ss03 unknown | same | same |
| c. mutex: named / real not provable / fakes rejected | section 4 | unknown / 2 of 2 rejected / 3 of 3 | same |
| harness checks sp01, bo01, lp01, oc01, tt01 | section 4 | same answers | same answers |
| dev v2: real fixes | section 4 | 6 proven; `t5e594f` still does not build its situation | same |
| dev v2: shortcut, name-order edit, healthy run | section 4 | none counted fixed | same |
| demo control_loop, AI off | - | deadlock | deadlock |
| reproducibility path (`oc01 --twice`) | - | same-boot second count back; the v3 path still has none | same |

Rows that differ between the two rounds (verdict, kind, progress, reason class): 0. Boots that failed in these two
rounds: 0. A first attempt at the final rounds was stopped after it found the `t151018` regression (11.6); both
rounds were then run again in full on aa4feb4.

End to end with a fake client (real build, boot and verdict, twice): the hostile probe and the hostile include were
refused, the recorded fix was proven with all three pairs growing, 4 usage entries. Still no test against the API.
246 boots of this pass have saved raw output; about 20 more (end to end, reproducibility path, a restarted job) do not.

### 11.5 Runner and scorer

- Both baselines get `--allow-unknown`, every arm `QD_SMP=1` and the pinned model.
- The caller's `ANTHROPIC_*` is dropped. An empty key or missing env file stops before any boot.
- A failed arm, missing rows or a failed scorer ends `fail:...`, never `done`. A used output directory is refused.
- It runs its own checkout and records the commit. A worktree without `.venv` needs `QD_PYTHON`.
- A word outside the vocabulary hits nothing. A false alarm is what criterion D says: a hang kind or "unknown".
- Re-scoring the recorded v3, v4 and v5 rows gives byte-identical tables; none of those tables was edited.

### 11.6 Found, outside the six, still passing (both rounds)

| fake | result | why | options |
|---|---|---|---|
| a fix that edits its own message record in the guest (path built at run time) | **fixed, wrong** | programs run as root next to the observer and its recorder | state "not tamper-proof" and read every v6 fixed edit by hand, or observe from outside the program (a larger change) |
| low server raised above the CPU load, channel still fixed-priority | **fixed** | priorities of processes that take part in messaging are not compared (inheritance moves them) | count it as a valid remedy and say so, or reject edits that change a priority (this also rejects some right fixes) |

A literal record path in an edit is refused; that is a text check only.

The narrowed rule: a pair outside the judged hang that was already idle in the hung boot, with nothing in flight,
does not have to grow. Without it the right fix of dev v2 `t151018` was rejected (two low loops that the CPU load
keeps off the CPU before and after the fix). Without a judged hang every pair must grow.

What the stricter rule costs: a pulse or event whose arrival is not seen is never proven (signal events, clients
that never read). A pair that does not exchange within the observation window, and a start-up handshake inside
the judged hang, look stopped.

### 11.7 Could v3 to v5 have been affected? Records only

**Probe entries.** v3 to v5 hold 5 entries on 4 lines:

| file:line | id | command |
|---|---|---|
| `results/sealed3_20261117/ai.jsonl:3` | q03 | `cat q03/cfgd.c` |
| `results/sealed3_20261117/ai.jsonl:9` | q09 | `ls -la q09` |
| `results/sealed3_20261117/ai.jsonl:9` | q09 | `grep -n <pattern> q09/eeprom.c q09/cfgrouter.c` |
| `results/sealed3_20261117/ai.jsonl:13` | q13 | `cat q13/valve.c q13/alarmd.c q13/pumpctl.c` |
| `bench/sealed_v5_1118/scored_1118/ai.jsonl:8` | E08 | `grep -n MsgReply E08/stopsrv.c` |

`grep -c '"kind": "probe"'` counts lines, so it shows 4. **Correction to section 7:** "5 in the committed jsonl"
was incomplete. `runs/` is ignored but two files in it are committed, with 15 more entries from the build/boot set:
`runs/sealed_ai-only_1115.jsonl` lines 2, 5, 8 and 11 (9 entries) and `runs/sealed_ai_1115.jsonl` lines 2, 5, 8 and
11 (6 entries). None of the 20 uses a dangerous option or leaves the roots intended then. The untracked records in
main's `runs/` (40 files, 29 entries, duplicates possible) show none either. Those two committed files also carry
`/home/...` paths: clean them before the repository is public.

**Edits.** All 219 recorded actions of v3 to v5: none has a suspicious include, incbin, environment or record path.
A run that crashed before writing its row would not be in these records.

| question | answer |
|---|---|
| Can "false fix 0" (healthy labels) be inflated by the lax verifier? | No. No arm has a fixed row on a healthy label, and laxity can only add such rows. This covers healthy labels only. |
| Did a fix counted on a hang label stop exchanging messages at run time? | **Cannot tell**, for all 39 fixed rows and the 12 upper-bound rows of the recalculation: no second message count was recorded. |
| Does any of those edits have that shape in its text? | No. The 46 distinct edits were read: none bounds a send by a round count or a time. Reading is not proof. |
| Does any have another shape that passes wrongly or arguably? | Yes. v5 E03 naive (`naive.jsonl:3`) raises the server's priority and leaves the channel: the second row of 11.6. The known v3 q12 and q17 baseline fixes on unknown labels remove or self-post the wait. |
| Did anyone rely on "pulse nobody reads"? | No fixed row lists an unread pair (39 of 39). |
| Self-send? | One scenario has the shape, v4 D22, a deadlock label. No arm was credited with it. |
| Excluded v3 q16 (healthy) | A naive_x2 fix was stopped only by the thread-count rule. It is outside the scored 16. |

v6 rows now keep the rerun's structure with both counts, so the second question can be answered next time.

### 11.8 For the user to decide before the freeze

1. The guest threat model (11.6, first row).
2. Whether raising a server's priority is a fix (11.6, second row).
3. The costs accepted here: mutex hangs never fixed, unseen arrivals never proven, the new host requirements.
4. Merge this branch, then freeze on that commit. The author's worktree, the pool and the answers go outside `/tmp`.
5. The amount and the key's account (sections 8 and 9), then the 2-call check.

After 1 to 4 nothing found in these checks stands against the freeze commit. These checks are dev scenarios run
twice, not proof that no other fake passes.
