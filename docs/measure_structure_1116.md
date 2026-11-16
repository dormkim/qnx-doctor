# Hang doctor: «same message structure» verifier and the v2 sealed set (2026-11-16, second run)

States only: hung or running, TICK or none, a message pair exchanged or not. No QNX timing or performance numbers
(QNX licence 4.2(i)). Counts of messages are thresholds for the verifier (≥ 2), not rates.

## Why
On the first held-out run (`measure_holdout_1116.md`) the liveness-only verifier accepted 12 of the naive baseline's
13 fixes. 7 of them rewired `run.sh` or made a ring member stop sending. The program was alive again, but it no
longer did what it did before.

## What «fixed» means now (`qnx_doctor/structure.py`, `common/qd_trace.c`)
The fix still has to pass the old check (no cycle or chain, a stopped loop ticks again, no ticking loop stops,
no process gone). On top of that:

1. **Static**: a fix may edit only the program's `.c`/`.h` files. `run.sh`, `common/` and non-C files are
   rejected. So are replacements that reach around the recorder (`__real_`, `asm`, `dlsym`, `syscall`, ...)
   and fixes that remove a receive call from a file.
2. **Same processes**: processes are matched across the two boots by command line (from `pidin arg`), not by pid.
   None may be gone and none added.
3. **Same message pairs**: `qd_trace.c` is linked into every scenario program with `-Wl,--wrap` for each
   `MsgSend*`, `MsgSendPulse*` and `MsgReceive*` call. The program's source cannot opt out. Every pair that tried
   to send before the fix must, after it, complete at least 2 sends (MsgSend returned = the peer replied; a
   pulse was delivered). The receiver must also count at least 2 arrivals from that sender, if it reads its
   channel at all. A pulse instead of a synchronous send is fine; no send is not. A receiver that never calls a
   receive (the v1 starter only attaches a name) cannot count arrivals. Pulses to it are reported as `unread`,
   not rejected.
4. **Threads**: no thread is removed from any program process. A process that takes no part in messaging (the CPU
   load) keeps its threads' priorities and stays busy where it was busy.
5. **pid cross-check** (claims only, not part of «fixed»): the pids the AI cites must be in the code's cycle or chain.

Both arms (ours and the naive baseline) get the same rule text in their prompt.

### Attacks on the target (dev pool only, `bench/fake_fix_check.py`)
One v1 dev ring (4 members, all send first) and one v1 dev priority chain, with fixes written by hand:

| fix | expected | result |
|---|---|---|
| ring: pulse to the next member | fixed | fixed (first try: a rerun failed liveness under a busy pulse loop; fixed on the retry) |
| ring: `run.sh` peer renamed | rejected | rejected (static) |
| ring: one member stops sending | rejected | rejected: **alive again** (TICKs resumed), 2 pairs no longer exchange |
| ring: every member stops sending | rejected | rejected |
| chain: channel without `_NTO_CHF_FIXED_PRIORITY` | fixed | fixed (first try). On a second try, with 3 QEMU guests at once, the hung boot lost its client (see caveats) |
| chain: CPU-load threads removed | rejected | rejected (load process gone) |
| chain: CPU load lowered to priority 1 | rejected | rejected: **alive again**, the load's priorities changed |
| chain: client stops sending | rejected | rejected: **alive again**, the pair no longer exchanges |

All 6 shortcuts were rejected. 3 of them came back alive and would have passed the old verifier. Unit tests:
`tests/unit/test_structure.py` (19 cases).

### Rule change after seeing the v1 re-judge (before the v2 run)
The first version required arrivals at every receiver. On the v1 re-judge it rejected reply-first/pulse fixes
whose pulse goes to the v1 starter, which never receives by design. Changed (commit after 5e79421): arrivals are
required only from receivers that call a receive in the rerun. A fix that removes a receive call is rejected
statically, so this cannot be reached by deleting the receive. This change was made after looking at the v1
numbers. The v2 held-out run below used the changed rule from the start.

## A. v1 sets: the fixes recorded on the first run, re-judged (no new AI call)
`bench/rejudge_hang.py`: boot the original once with the new harness, then apply each arm's recorded fix. For the AI
arm that is the attempt that was accepted as run. For the naive arm it is its single fix. «Liveness-only» = accepted by
the first run's verifier.

| set | arm | kind found | false alarm | fixed, same structure | shortcut rejected | liveness-only accepted |
|---|---|---|---|---|---|---|
| held-out 20 | code | 20/20 | 0/7 | - | - | - |
| held-out 20 | AI (ours) | 20/20 | 0/7 | **10/13** | 2 | 13/13 |
| held-out 20 | naive | 20/20 | 0/7 | **4/13** | 9 | 12/13 |
| sealed 7 | code | 6/7 | 0/2 | - | - | - |
| sealed 7 | AI (ours) | 7/7 | 0/2 | 2/5 | 0 | 2/5 |
| sealed 7 | naive | 7/7 | 0/2 | 3/5 | 2 | 2/5 |

- **Naive, held-out**: of the 12 fixes the old verifier accepted, 8 are now rejected: 7 edit `run.sh` and 1
  (sb26e25) turns a waiter into a process that no longer sends. The 9th rejected shortcut, s5b174f, also edits
  `run.sh` (it had already failed as run).
- **Ours, held-out**: 3 of 13 are no longer accepted.
  - sa44ba6 and sdf2cea: the relay replies at once and pulses on, but the next relays ignore pulses and stop
    forwarding. Two pairs further down no longer exchange. That is a real change of behaviour, and the check found
    it in our own fixes.
  - s7628ec: the rerun output was damaged (no message records, fewer processes in the snapshot). All roles were
    ticking. This is a harness failure under a busy pulse loop, not a rejection on structure. It is counted as not fixed.
- 5 of our 10 accepted fixes (s46856b, s56f19a, s5b174f, s869054, sb26e25) have one `unread` pair each: a pulse
  to a process that never calls a receive (the v1 starter). The naive arm's s56f19a fix has the same pair.
- Sealed 7: the code found no chain on D05 in this boot. The client of D05 was gone from the hung snapshot, so its
  chain did not form (see caveats). The AI column counts only fixes accepted as run (D03–D05 were rejected as run by
  the old TICK rule). It is not comparable to the post-hoc replay of the first run.

## B. v2 held-out 30 (sealed f19d090, generator v2.1 5e79421): first run
Run once, in this order: hashes checked (labels and scenario tree equal `sealed2.json`), code only, then AI ∥ naive.
Both fix arms were told the structure rules in their prompt. Raw: server `runs/st_1116/` (`v2_*.jsonl`, `score_v2.md`).

| arm | kind found | deadlock | chain | healthy | false alarm | fixed, same structure | shortcut rejected | false fix |
|---|---|---|---|---|---|---|---|---|
| code only | 30/30 | 15/15 | 10/10 | 5/5 | 0/5 | - | - | 0 |
| AI (ours) | 30/30 | 15/15 | 10/10 | 5/5 | 0/5 | **25/25** | 0 | 0 |
| naive | 30/30 | 15/15 | 10/10 | 5/5 | 0/5 | **20/25** | 0 | 0 |

Per axis (a scenario counts under every axis it has):

| axis | n | kind found (all arms) | AI fixed | naive fixed |
|---|---|---|---|---|
| confounder | 11 | 11/11 | 10/10 | 7/10 |
| runtime_mode | 14 | 14/14 | 12/12 | 8/12 |
| indirection | 16 | 16/16 | 15/15 | 11/15 |
| multi_file | 16 | 16/16 | 13/13 | 11/13 |
| runtime_prio | 6 | 6/6 | 5/5 | 5/5 |

- **Naming the kind is still not where we win.** The naive arm read the run-time masks in `run.sh` and the
  environment correctly and named all 30 kinds. The «source alone cannot tell» axes did not fool it.
- **The difference is in the fix.** All 5 naive misses are deadlocks, and all 5 have `runtime_mode`. It found the
  ring and tried to make one member serve first by name or by bit, in one reply and without a rerun. 3 reruns
  still showed the cycle. In 2 (t285e4e, t209465, both with a confounder), the cycle was gone but the rerun showed
  a priority chain, so they were not accepted. Why the chain appeared there is not examined yet (next: on dev).
- Ours: 24 of 25 passed on the first attempt. In t5ba6e5 the first attempt failed liveness, and the second passed.
  2 accepted fixes have an `unread` pair.
- **Shortcuts: 0 in both arms.** Both were told the rules, and neither edited `run.sh` or silenced a peer. The
  «without the check» picture is the v1 table above, where the naive arm was not told and 8 of its 12 accepted
  fixes were shortcuts. For the demo: v1 shows what a liveness-only check lets through; v2 shows that with the
  rules known, a one-shot fix still misses 5 of 25 that the rerun loop gets right.

## Caveats
- **Chains are sensitive to host load.** In the v1 generator and in sealed D05, the priority server lowers its
  priority before it writes its channel id to a file. With several QEMU guests on the host, the CPU load could
  starve that write. The client then gave up and exited, and no chain formed. This was found on dev v2 seed t7e9e6a
  and fixed in v2.1 (the id is written first; labels unchanged, checked by hash). v1 and D05 are unchanged because
  they are sealed.
- **Busy pulse loops can damage the rerun output.** The scenario processes inherit priority 50 from `hi`. A ring
  that pulses without blocking keeps the CPUs busy. Once (s7628ec) the snapshot came back incomplete.
- `unread` pairs are accepted. A fix that keeps a receive call in the source but never reaches it at run time
  would still pass when the hung boot shows no receive by that process. Not seen in these runs, and not closed.
- The structure rule was changed once after looking at the v1 re-judge (above). v2 is the clean number.
