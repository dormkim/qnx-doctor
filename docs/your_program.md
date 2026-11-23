# Putting your own QNX program under the gate

`qnx-doctor verify` does not need a program written for it. It needs four things around the program, and none of
them is a change to your message-passing code. The example in `examples/your_program/` is a pump driver and a
controller written with plain QNX 8.0 calls (`name_attach`, `name_open`, `ChannelCreate`, `ConnectAttach`, `MsgSend`,
`MsgReceive`, `MsgReply`). It includes no qnx-doctor header.

## What the gate needs

| # | What | In the example |
|---|---|---|
| 1 | A directory with the program's C sources. Every `.c` file is built into one executable with the same name | `examples/your_program/pump_ctl/pump.c`, `ctl.c` |
| 2 | A `run.sh` in that directory that starts the processes from `/var/qd/<directory name>/` in the background and returns a few seconds later | `examples/your_program/pump_ctl/run.sh` |
| 3 | One line that contains `TICK` for each completed round of a loop, in `/tmp/d0<role>.log`. Redirecting stdout in `run.sh` is enough | `printf("TICK %s %d\n", ...)` in both programs; `> /tmp/d0pcpump.log` in `run.sh` |
| 4 | The harness directory `common/` beside your directory (a link is fine) | `examples/your_program/common -> ../../tests/sealed_hang/common` |

The gate adds the rest when it builds: it links the message recorder into every program with `-Wl,--wrap`
(`common/qd_trace.c`), starts the observer before your `run.sh`, and reads `pidin` and the recorder's counts on the
target. Your sources are copied before each build; the gate never edits your directory.

A patch is a unified diff against the directory (`--- a/pump.c`, `+++ b/pump.c`), the output of `diff -u` or
`git diff`.

## The example, run on QNX 8.0 in QEMU

The pump serves "set speed" requests. After every third one it reports the speed back to the controller with a
synchronous send, while the controller is still waiting for the reply to its own request. Each waits for the other
and both loops stop.

```text
$ python3 -m qnx_doctor.cli hang --scenario examples/your_program/pump_ctl --no-ai
{"id": "pump_ctl", "mode": "code", "detected": "deadlock", "solved": false, "by": "code", "cause": null}

$ python3 -m qnx_doctor.cli verify examples/your_program/pump_ctl examples/your_program/patches/reply_first.diff
ACCEPT: the stopped loop runs again with the same message structure
{"id": "pump_ctl", "patch": "reply_first.diff", "verdict": "accept", "liveness_only": true, "structure_rule": true}

$ python3 -m qnx_doctor.cli verify examples/your_program/pump_ctl examples/your_program/patches/drop_report.diff
REJECT: alive again but the message structure changed: pair no longer exchanges messages: /var/qd/pump_ctl/pump pcpump -> /var/qd/pump_ctl/ctl pcctl pcpump (after the fix: 0 completed sends, 0 received; need 2 each)
{"id": "pump_ctl", "patch": "drop_report.diff", "verdict": "reject", "liveness_only": true, "structure_rule": false}
```

`reply_first.diff` replies to the controller before it sends the report. `drop_report.diff` deletes the report. Both
make the two loops run again; only the first keeps the pump reporting to the controller. These three outputs are
from our run of 2026-11-23.

This example is ours. We wrote the program and both patches knowing the rules, so it shows how to attach a program,
not how well the gate judges. The measurement on patches we did not write is in
[bench/sealed_v7_1123/RESULT.md](../bench/sealed_v7_1123/RESULT.md).

## What will not work yet

- A program whose executable is built from several `.c` files, or with its own build system. The gate compiles each
  `.c` file on its own with `qcc -Vgcc_ntox86_64`.
- Targets other than the x86_64 QEMU image the gate builds with `mkqnximage`.
- A hang that involves a thread waiting on a mutex. Lock use is not recorded, so no fix is accepted.
- An exchange that the program makes only once in its run. The rule asks every pair to keep exchanging messages, so a
  fix of such a hang is rejected (3 of 17 genuine fixes in our measurement).
- A loop that logs nothing. Without the `TICK` lines the gate cannot tell a stopped loop from a quiet one.

To look at a program on a running target without any of this, `hang --live` reads `pidin` over a transport and names
the hang; it does not judge a fix ([docs/live_attach_1116.md](live_attach_1116.md)).
