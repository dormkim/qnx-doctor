# Attach to a running target: design and first round (2026-11-16)

Goal: use qnx-doctor on a QNX system that was not built with our test harness. No `run.sh`, no TICK logs, no
`-Wl,--wrap` recorder, no observer program on the target. qnx-doctor only needs a way to run one shell line on the
target.

## Design

```
host                                         target (QNX 8.0, already running)
qnx-doctor hang --live "<transport>"  --->   for i in 1 2 3: pidin > /dev/shmem/qdl.$i; sleep 1
                                             print the three snapshots, then `pidin arg`
waitgraph.judge (code)                <---   text back over ssh / serial
  cycle, priority chain, missing reply
  + command line of each process involved (`pidin arg`)
  + optional --src DIR: message-passing call sites in the matching C files
```

- Transport: any command that takes the shell line as its last argument. On a board: `ssh root@<target>`.
  For the QEMU demo: `bench/qd_after_startup.sh IMAGE_DIR` (boots the image with `bin/qd-target-exec`, waits until
  the image's own startup script has finished, then runs the line).
- Same judge as the test loop (`qnx_doctor/waitgraph.py`), same rule: a priority chain or missing reply counts only
  if the same waiter → server pair is in all three snapshots; a cycle needs one.
- Snapshots go to `/dev/shmem` first and are printed afterwards, so the capture writes nothing while it looks.
- Read-only. It does not change, restart or kill anything on the target.
- If no pidin output comes back, it is an error, not "no hang" (`tests/unit/test_live.py`).

## First round (one run, our demo program, external path only)

`bench/live_demo.sh` on the server:

1. `scenarios/hang_demo/control_loop/loop.c` built with plain `qcc -Vgcc_ntox86_64` (no `qd_trace.c`, no
   `qd_start.c`, no `--wrap`).
2. An image where the system starts the program by itself at boot (`mkqnximage` `post_start` snippet: actuator,
   control, then sensor), with no harness files on it.
3. `qnx-doctor hang --live "bench/qd_after_startup.sh <image>" --src scenarios/hang_demo/control_loop`.

Output (pids are from that boot):

```
DEADLOCK: 638996(var/app/loop, SEND-blocked on 638997) -> 638997(var/app/loop, REPLY-blocked on 638996) -> 638996;
waiting behind the cycle: 679958(var/app/loop, REPLY-blocked on 638997)
  pid 638996: /var/app/loop actuator
  pid 638997: /var/app/loop control
  pid 679958: /var/app/loop sensor
message-passing calls in the matching sources (places to look, not a proof):
  loop.c:21 / :24 / :37  MsgReply(...)
```

All three processes run the same binary, so the roles are told apart only by `pidin arg`. The verdict is the same
kind the test loop gives for this program (actuator ↔ control cycle, sensor waiting behind it). The raw capture is
kept as `tests/unit/fixtures/live_control_loop_1116.txt`.

The first two attempts of this round found nothing, and both were our mistakes: the capture ran before the image's
startup script had started the program. `bench/qd_after_startup.sh` now waits for the startup script to finish.

## Limits

- **It names the hang; it does not fix it.** Fix and rerun need the build → image → boot loop, which is still our
  test harness (`hang --scenario`). On a running system there is no copy to edit and rerun.
- **No "same message structure" check.** That needs the `--wrap` recorder linked into the program.
- **Source pointers are a text match.** `--src` lists `MsgSend*`/`MsgReceive*`/`MsgReply`/... calls in C files named
  like the binary. Calls made through a helper in a header (our demo's `qd_send()` in `qd.h`) are not listed, and a
  binary with a different name than its source file gets no pointers.
- **Only what `pidin` shows.** SEND/REPLY waits between processes, priorities and thread states. Mutex and condvar
  waits inside one process, and errors that do not block (for example a missing `_NTO_SIDE_CHANNEL`), are not seen.
- **One round, one program.** It ran once on our own demo. It has not been run on a program we did not write, on
  a board, or over ssh. The QEMU guest has no network here, so the ssh path is untested.
- **Root shell needed** on the target for `pidin` to see every process.
