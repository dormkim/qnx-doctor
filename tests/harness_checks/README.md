# Harness checks

Small scenarios that test the harness itself (tracer, observer), not qnx-doctor. They are not a benchmark and are
never scored. Run one with `python3 bench/harness_check.py tests/harness_checks/<id>`.

- `tt01`: kernel timeouts must survive the qd_trace wrappers. `waiter` arms a RECEIVE timeout on a channel nobody
  sends to; `cli` arms a SEND timeout on a raw channel (`ChannelCreate`, side-channel `ConnectAttach`) that nobody ever receives on. Both loops must keep ticking (each call
  times out and the loop goes on). Before the 2026-11-17 fix the wrappers made kernel calls of their own before the
  real call, which used up the timeout (found while analysing sealed v3 q10; docs/분석_sealed3_1117.md).

- `lp01`: a slow server, not a lost reply (liveness by progress, 2026-11-17). `late` keeps each request and answers it
  on the next timer pulse; `asker` sends in a loop. Every snapshot shows asker REPLY-blocked on a server waiting in
  RECEIVE, which is what a missing reply looks like (`state_only`). Expected: asker's TICK count grows between the two
  counts, so the judge drops the wait and says healthy (`detected none`).
- `sp01`: a CPU spin after a few rounds. `meter` stores five readings with `store`, then busy-waits on a flag nobody
  sets. Expected: TICK count flat, meter RUNNING/READY in every snapshot, `detected unknown (spinning)`, not healthy.
- `bo01`: a stop outside message passing. `feeder` ticks three times, then waits on a semaphore nobody posts.
  Expected: `detected unknown (blocked_other)` naming the SEM state.
- `oc01`: a priority chain under a CPU load above the disk driver, for the observer fix. `slow` serves a
  fixed-priority channel at 5, `ctl` at 30 sends to it, `load` spins two threads at 22. Expected: judged
  `priority_chain`. With `--twice`, both reproducibility paths of `bench/repro_v3.py`: the v3 one (a second observer
  woken after check.sh) gives no second count, as on v3 q02, q06, q09, q21; the v4 one (`--same-boot`, snap's own
  TICKS and TICKS2) gives both counts.

Run all of them with the doctor's code judgment only (no AI): `python3 bench/harness_check.py tests/harness_checks/<id>`
(add `--twice` for the second-observer path). Each boots QEMU once and takes the one-QEMU lock.
