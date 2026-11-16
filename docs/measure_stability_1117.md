# Hang harness: steady verdicts and QNX trap scenarios (2026-11-17, dev pool only)

States only: hung or running, TICK or none, which threads were runnable at the snapshot. No QNX timing or
performance numbers (QNX licence 4.2(i)). Raw rows: server `runs/stab_1117/*.jsonl`. Tool: `bench/stability_check.py`
(same hand-written fix, N reruns, one QEMU guest at a time). Held-out and sealed sets were not opened or changed;
the v2 held-out hashes were regenerated and still match `sealed2.json`.

## What changed in the harness (cc04b2b, 2de0f3c)
1. **Programs at priority 10.** `common/qd_start.c` (linked like `qd_trace.c`) sets each scenario program to the normal
   QNX priority at start. Before, they inherited 50 from `hi`, above the serial driver (25) and the disk driver (21).
   Roles that set a priority themselves (server, client, CPU load) still do.
2. **Quiet snapshot.** `snap` prints nothing until both `pidin` runs are done. `pidin` writes to `/dev/shmem`.
3. **Chains must persist.** Two more `pidin` snapshots follow a moment later. A priority chain or a missing reply
   counts only if the same waiter → server pair is in all three. Deadlocks are judged on the first (a cycle cannot clear).
4. **One QEMU at a time.** `bin/qd-target-exec` takes a host-wide lock, so parallel arms queue.

## Why the two held-out reruns showed a chain (cause)
In both naive-arm cases (t285e4e, t209465, v2 held-out, recorded result only), the rerun's chain named
`devc-ser8250` at priority 25 as the middle thread, between the fixed-priority server (4) and its client (26, 32).
Both scenarios carry the confounder: a fixed-priority server whose CPU load sits below it. While the ring was hung,
the judge reported the cycle first; once the ring ran, the chain check was reached.

On dev, the old harness was compared with the new one on two confounder rings (t54e3fe, t6dd334) fixed with a pulse,
8 reruns each:

| harness | snapshots with the serial driver runnable | reruns with a verdict other than «fixed» |
|---|---|---|
| old (`snap` prints a header, then runs `pidin`; programs at 50; one snapshot) | 18 of 18 | 3 of 16 |
| new | 0 of 18 | 0 of 16 |

- The serial driver was runnable in every old snapshot: `snap` printed "=== PIDIN ===" to the console right before
  `pidin` looked, which woke the driver. It sits inside the band between the server and the client of every v2 chain
  (3–8 and 25–40). Whenever the server is busy with a request at that instant, the snapshot shows an inversion.
- The 3 wrong verdicts on the old harness were `missing_reply` (judged with today's judge on one snapshot): `pidin`
  does not read all processes at the same instant, so a client could be seen REPLY-blocked after its server had
  already replied and gone back to RECEIVE. The three-snapshot rule removes that too.
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

**Open: the MsgDeliverEvent fix is rejected, 3 of 3 (steady, but wrong).** The client ticks again (alive), so the event
is delivered, yet `qd_trace` records no completed send from the server to the client. The tracer names the client from
the rcvid saved with the event. That rcvid was already replied, so MsgInfo fails, and the rcvid cache did not match
either (also with a deduplicated cache of 64). Until this is fixed, a correct MsgDeliverEvent fix counts as «pair no
longer exchanges». Next: record the client pid when the event is handed over, or match on the event's connection.

## Caveats
- The judge changed today (persistence rule, new kind) after looking at two held-out results. All tuning was on dev.
  The held-out v2 numbers stay as run; they are not re-judged with the new rule. The next clean number is the new
  sealed set (11/19–21).
- v1 sets and sealed D01–D07 use the same `common/`, so a rerun of them now uses the new harness.
