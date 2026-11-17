# Harness checks

Small scenarios that test the harness itself (tracer, observer), not qnx-doctor. They are not a benchmark and are
never scored. Run one with `python3 bench/harness_check.py tests/harness_checks/<id>`.

- `tt01`: kernel timeouts must survive the qd_trace wrappers. `waiter` arms a RECEIVE timeout on a channel nobody
  sends to; `cli` arms a SEND timeout on a raw channel (`ChannelCreate`, side-channel `ConnectAttach`) that nobody ever receives on. Both loops must keep ticking (each call
  times out and the loop goes on). Before the 2026-11-17 fix the wrappers made kernel calls of their own before the
  real call, which used up the timeout (found while analysing sealed v3 q10; docs/분석_sealed3_1117.md).

