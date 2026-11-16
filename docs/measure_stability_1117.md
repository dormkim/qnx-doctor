# Hang harness: steady verdicts and QNX trap scenarios (2026-11-17, dev pool only)

States only: hung or running, TICK or none, which threads were runnable at the snapshot. No QNX timing or
performance numbers (QNX licence 4.6(i)). Raw rows: server `runs/stab_1117/*.jsonl`. Tool: `bench/stability_check.py`
(same hand-written fix, N reruns, one QEMU guest at a time). Held-out and sealed sets were not opened or changed;
the v2 held-out hashes were regenerated and still match `sealed2.json`.

## What changed in the harness (cc04b2b, 2de0f3c)
1. **Programs at priority 10.** `common/qd_start.c` (linked like `qd_trace.c`) sets each scenario program to the normal
   QNX priority at start. Before, they inherited 50 from our `hi` launcher, above the priorities the image's serial
   and disk drivers run at, so a busy scenario program could hold up our own observer's console output and file reads.
   Roles that set a priority themselves (server, client, CPU load) still do.
2. **Quiet snapshot.** `snap` prints nothing until both `pidin` runs are done. `pidin` writes to `/dev/shmem`.
3. **Chains must persist.** Two more `pidin` snapshots follow a moment later. A priority chain or a missing reply
   counts only if the same waiter → server pair is in all three. Deadlocks are judged on the first (a cycle cannot clear).
4. **One QEMU at a time.** `bin/qd-target-exec` takes a host-wide lock, so parallel arms queue.

## Why the two held-out reruns showed a chain (cause)
In both naive-arm cases (t285e4e, t209465, v2 held-out, recorded result only), our judge's chain named
the serial driver process (`devc-ser8250`, listed at priority 25) as the middle thread, between the fixed-priority server (4) and its client (26, 32).
Both scenarios carry the confounder: a fixed-priority server whose CPU load sits below it. While the ring was hung,
the judge reported the cycle first; once the ring ran, the chain check was reached.

On dev, the old harness was compared with the new one on two confounder rings (t54e3fe, t6dd334) fixed with a pulse,
8 reruns each:

| harness | snapshots with the serial driver runnable | reruns with a verdict other than «fixed» |
|---|---|---|
| old (`snap` prints a header, then runs `pidin`; programs at 50; one snapshot) | 18 of 18 | 3 of 16 |
| new | 0 of 18 | 0 of 16 |

- In every old snapshot our harness itself had just written "=== PIDIN ===" to the console, and the serial driver
  process was listed as runnable. Its priority falls inside the band between the server and the client of every v2
  chain (3–8 and 25–40), so our judge read an inversion whenever the server was busy with a request at that
  instant. This is a fault of our observer (it printed while looking), fixed by printing nothing until it is done.
- The 3 wrong verdicts on the old harness were `missing_reply` (judged with today's judge on one snapshot). Our judge
  had treated one snapshot as one instant; a client listed REPLY-blocked next to a server already back in RECEIVE is a
  passing state from our tool's point of view, not a stuck one. The three-snapshot rule removes that too.
- The exact chain verdict did not come back in 16 dev reruns on the old harness. So the cause is shown by its
  mechanism (the middle thread named in held-out is runnable in every old snapshot and in none of the new ones), not
  by a reproduced chain.

## Acceptance: the same fix 3 times, the same verdict (new harness)

| scenario (dev) | kind (first boot) | fix | 3 reruns |
|---|---|---|---|
| t54e3fe (confounder ring) | deadlock | mode bit replaced by name order (like the naive fixes) | deadlock ×3 (still hung: waiters break the alternation) |
| t54e3fe | deadlock | pulse to the next member | fixed ×3 |
| t6dd334 (4-ring, confounder) | deadlock | pulse | fixed ×3 |
| t151018 | priority_chain | channel without `_NTO_CHF_FIXED_PRIORITY` | fixed ×3 |
| tcb2750 (healthy) | none | no change | none ×3 |
| trap notify_back t363df3 | deadlock | reply first, then MsgSendPulse | fixed ×3 |
| trap fixed_flags t5e594f | priority_chain | flag removed from the header | fixed, fixed, **client gone** → see below |
| trap missing_reply t9273af | missing_reply | MsgReply on the hello path | fixed ×3 |

The fixed_flags miss: the client exited before the chain formed. Likely cause: the server writes its id file in place,
and the client (higher priority) can open it while it is still empty and exit. With programs now at 10 the client
can preempt the server in that window. The trap now writes a temp file and renames it (909103c); rerun below.
gen2's servers (sealed v2 held-out) write the file in place too. That cannot change (sealed); it is a known risk
for any rerun of v2 held-out under the new harness.

Rerun after 909103c (fresh dev pool): t5e594f chain on the first boot, then **fixed ×3**. With that, every case in
the table gives the same verdict 3 times in a row.

## QNX trap scenarios (dev pool only, `tests/gen_hang/traps.py`)
- **notify_back**: the server sends synchronously to its client before replying, while the client is REPLY-blocked
  on it (the «sends go one way» rule in the MsgDeliverEvent() docs). Judged as a deadlock (cause `send_on_reply_path`).
  QNX fixes: reply first, then MsgSendPulse; or the client registers a pulse event (MsgRegisterEvent) and the server
  delivers it (MsgDeliverEvent). `qd_trace.c` now records MsgDeliverEvent as a send (`S E`).
- **fixed_flags**: `_NTO_CHF_FIXED_PRIORITY` hidden in a flag constant in a header, next to `_NTO_CHF_DISCONNECT`;
  CPU load between server and client priority. Judged as a priority chain.
- **missing_reply**: the server takes the client's first message (a hello) on a path with no MsgReply, while it keeps
  serving another client. New judge kind `missing_reply`: a thread REPLY-blocked on an application process whose
  threads are all RECEIVE-blocked (system processes are left out: a resource manager holding a read is normal).
  New cause label `missing_reply` in the AI prompt and the naive prompt.
- **_NTO_SIDE_CHANNEL missing: not added.** The failures found so far for a connection id in the file-descriptor
  range are errors (EBADF, ENOSYS) or a wait on procnto (pid 1, outside the graph), not a wait between two programs.
  It needs a different symptom (error path) before it fits this judge.

**Open (fixed the same day, see «MsgDeliverEvent fix accepted» below): the MsgDeliverEvent fix is rejected, 3 of 3 (steady, but wrong).** The client ticks again (alive), so the event
is delivered, yet `qd_trace` records no completed send from the server to the client. The tracer names the client from
the rcvid saved with the event. That rcvid was already replied, so MsgInfo fails, and the rcvid cache did not match
either (also with a deduplicated cache of 64). Until this is fixed, a correct MsgDeliverEvent fix counts as «pair no
longer exchanges». Next: record the client pid when the event is handed over, or match on the event's connection.

## Caveats
- The judge changed today (persistence rule, new kind) after looking at two held-out results. All tuning was on dev.
  The held-out v2 numbers stay as run; they are not re-judged with the new rule. The next clean number is the new
  sealed set (11/19–21).
- v1 sets and sealed D01–D07 use the same `common/`, so a rerun of them now uses the new harness.

## MsgDeliverEvent fix accepted (2026-11-16 evening; plan item «11/18»)
Raw rows: server `runs/ev_1116/` (`stab_event.jsonl`, `fake.jsonl`). Dev pools only (`/tmp/qd_dev_ev2` = dev v2 +
traps, `/tmp/qd_dev_ev1` = the v1 dev pool of `fake_fix_check.py`, both with the new `common/`). Held-out and sealed
sets were not opened or run.

**Cause** (a bug in our code, probe on dev t363df3, one boot): `rcvid_t` is a 64-bit type in the QNX 8 headers, and
`qd_receive()` in our `common/qd.h` returns `int`, so our program kept only the low half and passed that to
MsgDeliverEvent. The client counted every pulse, so the event arrived; but our recorder looked the client up by the
full 64-bit value, found no entry for the value the program used, and never wrote an `S E` line.

**What changed** (`common/qd_trace.c`, `qnx_doctor/structure.py`, `qnx_doctor/hang.py`):
1. Server end: the rcvid → client pid cache is keyed by the low 32 bits (what a program that stores the rcvid in an
   `int` still has, and what the kernel accepted). One entry per client slot, so it no longer ages out.
2. Client end (new): `MsgRegisterEvent` is wrapped too. When a client registers a pulse event, `G E <server pid>`
   is written (the coid names the only server allowed to deliver it). A pulse with that code arriving on the
   client's own connection (how a delivered SIGEV_PULSE looks to the receiver) is counted as `R E <server pid>`.
3. Verifier: an event pair now needs both ends, like a message or a pulse: ≥ 2 events delivered by the server to
   that client, and, when the client registered a pulse event for that server, ≥ 2 arrivals at the client. A signal
   event (or no registration seen) cannot be counted at the client; that pair is reported as `unread`, not rejected.
   Unit tests: `tests/unit/test_structure.py` (`DeliverEvent`, 7 cases).

**Results (dev, new harness, one QEMU guest at a time)**

| scenario (dev) | fix | expected | 3 reruns |
|---|---|---|---|
| trap notify_back t363df3 (first boot: deadlock) | reply first, then MsgSendPulse | fixed | fixed ×3 |
| t363df3 | client registers a pulse event (MsgRegisterEvent), server replies, then MsgDeliverEvent | fixed | **fixed ×3** (was «pair no longer exchanges» ×3) |
| t363df3 | shortcut: event registered, server never delivers, client pulses itself with the same code | rejected | rejected ×3, alive again each time: the client side shows arrivals, the server side shows no event sent |

One more rerun of the MsgDeliverEvent fix (`event_pairs.jsonl`) shows the pair counted at both ends (sends done,
registration seen, arrivals counted) and no `unread` pair, so it passes on the event records, not by skipping the
client side.

The six shortcuts of `bench/fake_fix_check.py` (v1 dev ring s9370e5, v1 dev chain s31f015), with the new recorder:

| fix | expected | result |
|---|---|---|
| ring: pulse to the next member | fixed | fixed |
| ring: `run.sh` peer renamed | rejected | rejected (static) |
| ring: one member stops sending | rejected | rejected: alive again, a pair no longer exchanges |
| ring: every member stops sending | rejected | rejected |
| chain: channel without `_NTO_CHF_FIXED_PRIORITY` | fixed | fixed |
| chain: CPU-load threads removed | rejected | rejected (load process gone) |
| chain: CPU load lowered to priority 1 | rejected | rejected, but this time because the **client was gone** (not on the load's priorities as on 11/16) |
| chain: client stops sending | rejected | rejected: alive again, the pair no longer exchanges |

All 6 shortcuts are still rejected. The «CPU load lowered» row was rejected for a different reason than before: the
v1 chain client exited (the known v1 id-file race, see «Caveats» of `measure_structure_1116.md`; v1 is sealed and
keeps it). That row does not show the load-priority rule working on this run.

**Why and when the rule changed.** The verifier rule for event pairs was changed on 2026-11-16 after seeing the
dev result above (3 of 3 correct MsgDeliverEvent fixes rejected). It is a rule changed after looking at results.
The v2 held-out numbers stay as run and are not re-judged. The first clean measurement with this rule is the new
sealed set (11/19–21).

## Design note: symptoms the wait graph cannot show (`_NTO_SIDE_CHANNEL` missing) — not implemented
- **The symptom.** `ConnectAttach()` without `_NTO_SIDE_CHANNEL` returns a connection id in the file-descriptor
  range. Nothing blocks: the failure shows up as an error (EBADF after the program closes or `dup2`s «its» fds,
  ENOSYS when a stray `read`/`write` reaches the program's own server as an `_IO_*` message), or a child process
  inherits the connection. `pidin` shows no SEND/REPLY edge between two programs, so the hang judge sees nothing.
- **Observe** (same recorder, no new tool): wrap `ConnectAttach` and record `A F <server pid> <coid>` when the flags
  lack `_NTO_SIDE_CHANNEL`; record failed sends with their errno (`S M <peer> ...` already counts attempts vs done;
  add the errno). On the server side, count `_IO_*` messages from a client that never opened it by path (today
  `qdt_got` drops them as name_open traffic).
- **Judge**: a new kind `fd_range_coid` only with run-time evidence: an fd-range coid AND (failed sends with EBADF,
  or `_IO_*` traffic from that client, or the coid seen in a child). A missing flag in the source alone is a hint for
  the AI, not a verdict.
- **Fixed**: the rerun shows the same connection in the side-channel range, no failed sends, and the same message
  pairs (existing rule).
- **Before adding a trap** (dev pool only): reproduce the error path 3 of 3 on the target first, as for the other
  traps.
