# qnx-doctor

A host tool for QNX 8.0 that finds why something is stuck or broken, proposes a fix as data, applies it to a copy, and re-runs it. It only says "solved" when the re-run shows the problem is gone.

Two doctors share one engine:

- **Blocked-chain doctor** (`hang`): a QNX program stops making progress. qnx-doctor boots the image in QEMU, takes a `pidin` snapshot on the target, and builds the wait-for graph in code. SEND/REPLY edges point at the peer process. From that graph it finds cycles (deadlock), the processes waiting behind them, and priority chains: a high-priority client waits on a READY low-priority server while a middle-priority thread is runnable (RUNNING or READY). The AI then reads the graph, the source and the QNX docs that ship with the SDP. It returns `edit_file` actions. Code applies them to a copy, rebuilds with `qcc` and runs the image again. The hang counts as fixed only if the re-run shows no cycle or chain, a loop that had stopped prints TICK lines again, no loop that was running stops, and **the program keeps the same message structure**: the fix edits only the program's C sources (not `run.sh`, not the harness), the same processes run (matched by command line, not pid), every pair of processes that tried to send before still completes sends and the receiver still gets them (a pulse instead of a synchronous send is fine; no send is not), no thread is removed, and a process that takes no part in messaging (a CPU load) keeps its priorities and its load. Message pairs come from `common/qd_trace.c`, which the harness links into every scenario program with `-Wl,--wrap` for each `MsgSend*`, `MsgSendPulse*` and `MsgReceive*` call, so a fix cannot opt out. A «fix» that rewires `run.sh`, makes one peer stop sending, removes the load's threads or lowers its priority comes back alive but is rejected as a shortcut.
- **Build/boot doctor** (`run`, `diagnose`, `bench`): a host command fails (SDP not sourced, wrong target, broken `mkqnximage` call, and so on). A rule table runs first. Then the AI looks around with read-only commands and searches the docs. It returns a fix as data, and the command is re-run.

The AI never runs a command that changes the system. Fixes are limited to an allow-list of data actions (see `qnx_doctor/actions.py`). In hang mode only `edit_file` is allowed, and the AI may only read paths inside the working copy.

## Requirements

| | |
|---|---|
| QNX version | QNX SDP 8.0 (`qnx800`), installed on a Linux host |
| Target | x86_64 QNX 8.0 guest in QEMU, built with `mkqnximage --type=qemu --arch=x86_64` (no hardware needed) |
| Toolchain | `qcc -Vgcc_ntox86_64` from the SDP; `mkqnximage` from the SDP |
| Host | Linux x86_64 (tested on Ubuntu 24.04); Python 3.10+; `qemu-system-x86_64` (KVM is used when `/dev/kvm` is writable) |
| AI | `pip install anthropic`, plus `ANTHROPIC_API_KEY` in the environment. Model: `QD_MODEL`, default `claude-opus-5-5`. Not needed with `--no-ai` |

Environment: `QNX_SDP` (default `~/personal/qnx/qnx800`) and `QD_QEMU_ROOT` (a QEMU install root; default `~/personal/qemu_local/root`).

## Build and run

```sh
git clone <this repo> && cd qnx-doctor
python3 -m qnx_doctor.cli index                       # once: index the QNX docs installed with the SDP

# Hang: read-only analysis of a pidin capture (no SDP needed)
python3 -m qnx_doctor.cli hang --pidin tests/unit/fixtures/pidin_dl2_1115.txt

# Hang: full loop on a scenario: build with qcc → image → boot in QEMU → graph → AI fix → rebuild → re-run
python3 -m qnx_doctor.cli hang --scenario scenarios/hang_demo/control_loop --out runs/demo.jsonl
python3 -m qnx_doctor.cli hang control --scenario scenarios/hang_demo/control_loop --no-ai   # name the hang only, focused on "control"
python3 -m qnx_doctor.report runs/demo.jsonl --id control_loop --html demo.html            # timeline for people

# Build/boot doctor on any failing command (fixes are tried on a copy of the current directory)
python3 -m qnx_doctor.cli run -- make -C myproject
```

A hang scenario is a directory with `*.c` sources and a `run.sh` that starts the processes. On the target, `check.sh` first starts the observer `snap` (so it is already loaded), then runs `run.sh`. When `run.sh` returns, it wakes `snap` with the shell builtin `kill`. At priority 63, `snap` counts the TICK lines in each `/tmp/d0<role>.log` and prints a `pidin` snapshot. The observer must be loaded before the scenario starts: `/var` and `/tmp` are on the disk image, and a CPU hog above the disk driver's priority would otherwise delay the observer until the hang had cleared. A sibling `common/` directory holds `qd.h`, `snap.c`, `hi.c` and `check.sh`. See `scenarios/hang_demo/`.

## How it is measured

- `tests/sealed_hang/`: 7 hand-written scenarios with an answer key, sealed before the judge existed. Five are faults (2-way and 3-way SEND cycles, a REPLY chain behind a cycle, a synchronous callback, a priority chain on a fixed-priority channel). Two are healthy systems that must not be reported (a slow server, and idle receivers fed by pulses).
- `tests/gen_hang/`: seeded random generators. v1 (`gen.py`): Each scenario has 2–6 processes, a random cycle length, mixed SEND/REPLY waits, waiters behind the cycle, decoys with long but legitimate waits, and random names and layout. The answer key is written outside the scenario directories. The `dev` seeds are for development. The `heldout` seeds were sealed before tuning, and results are reported on held-out only. v2 (`gen2.py`, sealed with answer-key hashes in `sealed2.json`) draws more priority chains and adds cases where the source alone does not tell which hang happens: ring members that pick «send first» or «serve first» from a bit mask given at run time (argument or environment), a second hang pattern that does not fire at run time (a fixed-priority server whose load sits below it, or a mixed-mode ring) with logs that show no TICK, run-time priorities, a chain that clears before the snapshot, roles split over several programs, and a name table.
- Arms: AI off (code names the hang, no fix) vs AI on (fix + re-run) vs a naive baseline (`bench/naive_hang.py`): the same model reads only the source and the TICK logs, with no `pidin` snapshot, wait graph, docs or probes, and its fix goes through the same re-run check. False "solved" on healthy controls must be 0. Scoring: `bench/score_hang.py` and `bench/score_structure.py` (the only code that reads the answer keys). `bench/fake_fix_check.py` attacks the verifier on the target with shortcut fixes on dev scenarios; `bench/rejudge_hang.py` re-judges recorded fixes without a new AI call.
- Only states are reported (blocked or running, TICK or no TICK). No QNX timing or performance numbers are published (QNX licence 4.2(i)).

Unit tests (no SDP needed): `python3 -m unittest discover tests/unit`.

## Layout

```
qnx_doctor/  waitgraph.py (pidin → graph → verdict, pure)  structure.py (same message structure, pure)  hang.py / hangdoctor.py (target loop)
             ai.py (look-around loop)  actions.py (fix allow-list)  docs.py (SDP docs index)  report.py (timeline)
             doctor.py / rules.py / runner.py (build/boot doctor)  cli.py
bin/         qd-target-exec (boot image in QEMU, run one command, return its status)  qd-boot
tests/       unit/  sealed_hang/  gen_hang/  sealed/ (build/boot set)
scenarios/   hang_demo/control_loop (sensor → control → actuator)
```

Licence: Apache-2.0.
