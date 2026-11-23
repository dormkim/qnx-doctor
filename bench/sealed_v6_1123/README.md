# sealed_v6_1123

30 QNX 8.0 hang scenarios for the v6 sealed run, written blind (the author never saw the tool under test).

- `pool/<id>/`: one folder per scenario: C sources (each includes `../common/qd.h`) and `run.sh`, which starts every
  process in the background from `/var/qd/<id>/` and sleeps 4 s. Loop roles write `TICK <role> <n>` to
  `/tmp/d0<role>.log`. Multi-threaded programs open one such log per thread; their process stdout goes to
  `/tmp/<id>*.out`, which the observer does not count.
- `pool/common/`: an unchanged copy of `tests/sealed_hang/common/`.
- `answers/labels.json`: the key, one object per id (fields: `row`, `row_text`, `kind`, `accept_kinds`,
  `info_insufficient`, `loop_logs`, `axes`, `expect`, `states`, `culprit`, `fix`, `loads`).
  `answers/ids.md` describes the id shuffle. Which id belongs to which row of the mix is written only in `answers/`.

Key conventions:
- A role named `<proc>.main` is the main thread of a multi-threaded process. It has no log, and its `expect` is `any`.
- `loop_logs` lists the logs of loop roles whose `expect` is `ticks` or `stops`. A CPU-load role (listed in `loads`)
  prints at most one TICK, or ticks while spinning (grp), and has `expect: any` unless it ticks.
- `states` gives pidin's state word first. On one core, a CPU-bound thread is shown as `READY`, because the observer's
  pidin (priority 63) is the thread that is running.
- Priorities: loads 6-16 (all at or below 20), fixed-priority servers 4-6 via `qd_fixed_chan` only, high clients
  25-35.

Nothing here was compiled or run on the target. The C files were only syntax-checked on the author's Mac
against a stub of the QNX declarations.

## Files opened by the author on the build server
- tests/sealed_hang/common/qd.h
- tests/sealed_hang/common/qd_start.c
- tests/sealed_hang/common/qd_trace.c
- tests/sealed_hang/common/snap.c
- tests/sealed_hang/common/hi.c
- tests/sealed_hang/common/check.sh
- tests/sealed_hang/D01/pingpong.c
- tests/sealed_hang/D01/run.sh
- bench/run_sealed3.sh

Directory listings: `ls` of tests/sealed_hang/common, tests/sealed_hang/D01 and bench/ (bench/ held only
run_sealed3.sh); `git status --short`. Nothing else was opened, listed or searched.
