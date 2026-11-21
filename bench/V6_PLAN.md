# Sealed set v6: plan (written 2026-11-21, before the set exists; nothing here has been run)

v3, v4 and v5 are development sets now (`bench/DEVSET_RECALC_1121.md`). v6 is the one place where the claim is
measured, once. This plan fixes the criteria, the baseline change and the author brief before any scenario is
written, so the set is not shaped by what the tool needs.

## 1. What is claimed, and what decides it (written before the run)

Claim to be tested: **«qnx-doctor does not report a fix it has not proven, and says `unknown` when it cannot name
the cause — also against a baseline that is allowed to say `unknown`.»**
Not claimed, whatever the numbers: that ours fixes more than the baseline. Fixed counts are reported for all arms
and a tie is a normal result (v3 3 : 3, v4 5 : 5, v5 4 : 4 as recorded).

Arms, same model, one QEMU at a time, one run: `code` (AI off), `ours`, `naive` and `naive_x2`, the last two with
`--allow-unknown`.

| # | Criterion (counted by `score_structure.py`, fixed before the seal) | Adopt the claim if | Drop or reword if |
|---|---|---|---|
| A | false fix (fixed on a healthy label) + fixed on an unknown label, ours | 0 | 1 or more: the claim is dropped, the cases are published |
| B | the same count for the baselines | reported as is | if it is also 0 for both baselines (as in v4 and v5), the «unproven fix» half of the claim is written as «no arm reported an unproven fix on v6; v3 is the only set where a baseline did» |
| C | `unknown` labels hit, ours vs each baseline with `--allow-unknown` | ours higher than both by 2 labels or more | within 1 label: written as «a baseline that may say unknown matches the tool on unknown labels», and the 10 : 8 of v5 is described as a vocabulary effect. Baseline higher: said so in the first paragraph |
| D | false alarm on healthy labels (a hang kind or `unknown` on a healthy scenario), ours | not higher than either baseline | higher: reported next to C in the same sentence (saying `unknown` too often is the cost of C) |
| E | kind found, all labels | reported, no threshold | never used as the headline |
| F | fixed (same structure), first try and with retries | reported, no threshold | - |

The headline sentence uses A, B, C and D together, in that order. If the reproducibility check (section 4) leaves
fewer than 20 scenarios, or fewer than 4 `unknown` labels, the run is made but reported as «too small to decide C».
No criterion, scorer line, prompt or rule changes after the seal commit; if one must, the change and its reason
open the result document.

## 2. The baseline may say `unknown` (`bench/naive_hang.py --allow-unknown`)

Why: up to v5 the baseline's reply had four words (`deadlock`, `priority_chain`, `missing_reply`, `none`). On an
`unknown` label it could only score 0. In v5 the whole 10 : 8 gap was two such labels, and on both the baseline's
free-text cause was right (`bench/sealed_v5_1118/scored_1118/score.md`, last table).

Design (implemented and unit-tested, never run against a model: `tests/unit/test_naive_unknown.py`):
- Off by default, so every run up to v5 stays reproducible byte for byte (`system_prompt()` returns the old text).
- With the flag, two additions to the prompt and nothing else: `"unknown"` joins the kind list, and one sentence
  defines it with the meaning our tool gives the word (`progress.classify`): «a loop that should run has stopped,
  but the cause is not one of these three kinds or cannot be decided from what you have (for example a CPU loop, a
  wait outside message passing, or a cause that is not in the given sources)». «For none and unknown give no
  actions.»
- `unknown` ends the case like `none`: no rerun, no fix, no retry. The row records the vocabulary it was given.
- Scored exactly like ours: a hit on an `unknown` label, a false alarm on a healthy label, a miss on a hang label.
- Unchanged on purpose: the baseline still gets sources and TICK counts only (no pidin, no wait graph, no docs
  search). What the comparison isolates is therefore «the observation and the code judgment», not the word.
- Known asymmetry that stays: ours says `unknown` from code (the AI is not asked); the baseline's `unknown` is the
  model's own call. That is the comparison the claim is about.
- Feedback after a failed try now names the failed condition for every arm (TICK counts and processes; the wait
  graph text is still cut for the baseline).

Smallest check before the seal (needs 2 model calls and no boot of a sealed scenario; not done yet, needs an OK):
the harness checks `tests/harness_checks/sp01` (CPU spin) and `bo01` (blocked outside message passing) through
`naive_hang.py --allow-unknown`, only to see that the reply parses and the word can come out.

## 3. Author brief (a new session that has not seen this repository's code)

Who: a fresh agent in its own worktree (`git worktree add /tmp/qd_v6_author -b sealed-v6-author`, after the freeze
commit). It must not open `qnx_doctor/`, `bench/` (except `run_sealed3.sh` to see how scenarios are started),
`results/`, `runs/`, `docs/`, `README.md`, `JUDGES.md`, `tests/unit/`, `tests/harness_checks/`, any earlier pool or
answer key, or this file. It gets the brief below, the whole harness directory `tests/sealed_hang/common/` (all of
it from the start: in v4 a missing shared file cost a correction) and one example scenario (`tests/sealed_hang/D01`).
Its README lists every file it opened; the session transcript is kept.

Brief (pasted as is):
- Write 30 QNX 8.0 scenarios and an answer key in `bench/sealed_v6_<date>/{pool,answers}`, in the format of the
  example: programs include `../common/qd.h`; `run.sh` starts every process in the background from `/var/qd/<id>/`
  and sleeps 4 s. Ids are shuffled; names, comments and log lines read like a developer's, some mislead on purpose.
- Format rules: a loop program writes `TICK <role> <n>` to `/tmp/d0<role>.log`; a running loop prints a TICK at
  least every 500 ms; a program that ends on purpose prints no TICK. A fixed-priority server uses `qd_fixed_chan`
  from the harness, nothing else. The target runs on one core.
- The answer key per scenario: `kind` (`deadlock`, `priority_chain`, `missing_reply`, `multi`, `healthy`,
  `unknown`), `accept_kinds`, `info_insufficient`, `loop_logs`, `axes`, `expect` per role (`stops` / `ticks` /
  `any`), `culprit`, `fix`, and `states`: for every role, the thread state a `pidin` listing would show while the
  scenario is in its final situation, written with pidin's own state word first (`SEND`, `REPLY`, `RECEIVE`,
  `MUTEX`, `CONDVAR`, `SEM`, `JOIN`, `NANOSLEEP`, `RUNNING`, `READY`). The set is checked against these words
  before it is sealed; a scenario that does not show them comes back to you for repair, with only the words that
  were not seen.
- A CPU-load process must not run at a priority above the system's disk and console drivers; keep loads at
  priority 20 or below and say in the key which roles are loads.
- Mix (30):

| n | kind in the key | what it is |
|---|---|---|
| 2 | deadlock | a ring of synchronous sends in which every member prints at least one TICK before its first send |
| 2 | missing_reply | a server that replies for a few rounds and then stops replying on one code path |
| 2 | deadlock | two mutexes taken in opposite order by two threads |
| 2 | priority_chain | a low thread holds a mutex without priority inheritance while a middle thread runs |
| 1 | healthy | a mutex held for a long time by design; every loop keeps ticking |
| 1 | deadlock | a thread sends to a channel of its own process that no thread receives on |
| 1 | healthy | a thread sends to a channel of its own process; another thread of that process receives and replies |
| 2 | healthy | client and server keep exchanging messages next to a CPU-load process that takes no part in messaging and prints at most one TICK (one load above the server's priority, one below) |
| 2 | unknown | a single process ticks a few times, then spins on the CPU |
| 2 | deadlock | every thread of a server pool is busy in a synchronous send back to a client that waits for the pool (pool exhaustion) |
| 2 | deadlock | three or more clients and servers closing a cycle through a relay |
| 3 | unknown, `info_insufficient: true` | the loop stops for a cause that is not in the given sources (missing peer, missing file, external signal that never comes) |
| 3 | healthy | looks stuck in one snapshot (slow replies, long poll, timer-driven server) but keeps ticking |
| 3 | priority_chain | a high client waits on a `qd_fixed_chan` server kept off the CPU by a middle load |
| 2 | missing_reply | plain: one code path receives and never replies |

- Public QNX knowledge and common bug patterns only. Do not write about how QNX performs or what a QNX call does
  beyond its public documentation.

The first nine rows are the shapes named in the 2026-11-21 failure classification (section 4 of that note); the
next three rows cover shapes never measured (pool exhaustion, cycles with three or more parties, causes outside
the sources); the last three are controls. Mutex scenarios are in the set although the tool gives them no name
(expected answer from ours: `unknown`, a miss on those 4 hang labels, with the mutex lines shown in the reason). That
cost is taken on purpose, so that «says unknown» is measured where it is uncomfortable.

## 4. Gates before the seal (in this order)

1. **Freeze commit**: judge, verifier, scorer, prompts, harness. Everything in `bench/DEVSET_RECALC_1121.md` is in.
2. **Dev boot checks, dev pool and `tests/harness_checks/` only (not done yet; each needs a boot, none needs the
   sealed set):**
   - `bench/fake_fix_check.py` on a dev ring whose members print a TICK before the first send: the real fix must be
     fixed, every fake rejected, under the rule that now also reads the rerun's second count. If a real fix is
     rejected because the fixed loop does not grow between the two counts, the rule is corrected before the freeze.
   - one dev scenario for the self-send finding and one where a second thread receives (no deadlock named).
   - structure record and MUTEX threads: the first observation counts threads from the strict pidin parse, which
     drops threads in a MUTEX wait. On the dev sets this made a baseline's mutex fix look like «threads changed»
     (v4 D02, D10, D17, D22). Decide on a dev mutex scenario whether the structure record should read all threads;
     until then a mutex scenario cannot be fixed by any arm and the result document says so.
3. **Seal** (commit): sha256 of `answers/labels.json` and of the pool in `SEAL.md`, with the freeze commit.
4. **Reproducibility check**, no doctor: `bench/repro_v3.py POOL LABELS OUT --same-boot`. It now also runs
   `bench/repro_states.py`: every process run.sh starts is in the process list, and every thread state the label
   names is seen on a program thread. A scenario that fails goes back to the author once, with only the label's own
   words that were not seen; if it fails again it is excluded with the reason, the label is not edited. Stop rule:
   if 3 or more scenarios of one row of the mix fail for a harness reason, the run is not made and the harness
   failure is reported.
5. **Run once**: `bench/run_sealed3.sh` with the four arms; the script refuses a used output directory.
6. **Report**: the v6 table, the criteria of section 1 with the outcome of each, exclusions, per-axis table,
   literal outputs on `unknown` labels for every arm, first try vs retries. States only (licence 4.6(i)).

## 5. Calls and cost (estimate; token counts were never recorded)

Model: `claude-opus-5-5` (`qnx_doctor/ai.py`, `QD_MODEL`), the same for every arm.
Price used: $4 per million input tokens, $20 per million output tokens (thinking is billed as output). Source: the
model table of Anthropic's `claude-api` reference skill, cached 2026-11-03. **Check the live pricing page before the
run.**

Calls, counted from the recorded runs (one call = one model turn):

| set | scenarios | ours: turns (scenarios that reached the AI) | naive | naive_x2 (tries recorded) |
|---|---|---|---|---|
| v3 | 21 | 47 (12) | 21 | 26 |
| v4 | 24 | 14 (6) | 24 | 20 fix tries; at least 24 calls |
| v5 | 12 | 25 (8) | 12 | 12 fix tries; at least 12 calls |

Ours used 3.1 to 3.9 turns per scenario that reached the AI (hard limit: 2 fixes x 8 turns = 16). For 30 scenarios,
of which 18 have a hang label and at most those reach the AI (fewer if ours answers `unknown`):

| | expected | upper bound |
|---|---|---|
| ours | 18 x 3.5 = about 63 calls | 18 x 16 = 288 |
| naive | 30 | 30 |
| naive_x2 | about 45 | 60 |
| total | **about 140 calls** | **378 calls** |

Tokens per call are **not known**: the runs did not log `usage`. What can be said from the files: every call carries
the scenario sources and the whole harness directory (about 29 KB for `common/`, 1 to 4 KB per scenario) plus the
instructions, and each reply is capped at 4,000 output tokens (thinking included). Assuming 12,000 input tokens per
call for the baselines, 20,000 for ours (turns add up) and the full 4,000 output tokens every time:

- expected: about 140 calls, about 2.2 M input + 0.56 M output tokens = **about $20**
- upper bound: 378 calls at 20,000 + 4,000 tokens = 7.6 M input + 1.5 M output = **about $60**
- plus the 2 calls of the check in section 2 (cents).

These are assumptions, not measurements. No prompt caching is used. To replace them with a measurement, the v6 run
should log `response.usage` per call (not implemented). Per the 2026-11-21 decision the amount is told to the user
before the run, and the run waits for an OK.

Machine time (not money): each scenario is booted once per arm for the observation and once per fix try; with the
counts above that is roughly 30 (code) + up to 36 (ours: 18 x 2 fix tries) + up to 18 (naive) + up to 36 (naive_x2) boots, plus 30 for the reproducibility check, one QEMU at a time.

## 6. Known limits going in

- One core only (`QD_SMP=1`); priority chains on two cores are not measured.
- 30 scenarios, one run: differences of 1 label decide nothing (criterion C asks for 2).
- The progress check counts TICKs twice in one boot; a loop slower than the gap looks stopped. The 500 ms format rule
  is there for that, and the liveness rule for a fix now depends on it too.
- The reproducibility check for thread states is per scenario, not per role.
- Mutex waits are shown, not named. Whether the last value of a MUTEX line in pidin is the holding thread is not
  decided here.
- The author knows the vocabulary (it is in the key format) but not the code; the main session writes no scenario.
