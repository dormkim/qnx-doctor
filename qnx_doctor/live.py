"""Read-only hang check of a QNX 8.0 target that is already running, outside our test harness (2026-11-16).

No run.sh, no TICK logs, no `-Wl,--wrap` recorder, no observer program: qnx-doctor only runs `pidin` (three
snapshots a moment apart, the same persistence rule as the harness) and `pidin arg` through a transport the user
gives (`ssh root@target`, or `bin/qd-target-exec IMAGE_DIR` for a QEMU image), builds the wait-for graph in code
(waitgraph.judge) and names each process by its command line. With `--src DIR` it lists the message-passing call
sites in the sources whose file name matches a process involved, as places to look (a text match, not a proof).

  python3 -m qnx_doctor.cli hang --live "ssh root@10.0.2.15" [--src DIR] [name|pid]

Limits (see README «Attach to a running target»): it names the hang, it does not fix or rerun it (that needs the
build + image loop); without the recorder it cannot check «same message structure»; pidin does not read every
process at one instant, so a single snapshot can show a passing state (deadlocks still need only one: a cycle does
not clear by itself); thread names come from pidin, so a program that runs several roles from one binary is told
apart only by `pidin arg`. States only, no timing (QNX licence 4.6(i)).
"""
import os
import re
import shlex
import subprocess

from . import waitgraph as wg
from .runner import base_env

# One shell line: snapshots go to /dev/shmem first (RAM, served by procnto) and are printed afterwards, so the
# capture writes nothing to a console or network link while it looks (same reason as common/snap.c).
# Kept short: over a serial console a long input line is risky.
CAPTURE = ("for i in 1 2 3; do pidin > /dev/shmem/qdl.$i; sleep 1; done; "
           "for i in 1 2 3; do echo \"=== PIDIN$i ===\"; cat /dev/shmem/qdl.$i; done; "
           "echo '=== ARGS ==='; pidin arg; echo '=== END ==='; rm -f /dev/shmem/qdl.*")
CALLS = re.compile(r"\b(MsgSend\w*|MsgReceive\w*|MsgReply|MsgError|MsgDeliverEvent|ChannelCreate|name_attach|name_open)\s*\(")


def section(out: str, name: str) -> str:
    """Text after the LAST marker: a serial console echoes the command line, which holds the ARGS/END markers too."""
    return out.rsplit(f"=== {name} ===", 1)[1].split("===", 1)[0] if f"=== {name} ===" in out else ""


def capture(transport: str, timeout: int = 1200) -> str:
    """Run the capture line on the target through the user's transport; the command's own output is returned."""
    env = base_env()
    if "SSH_AUTH_SOCK" in os.environ:  # the user's transport may be ssh
        env["SSH_AUTH_SOCK"] = os.environ["SSH_AUTH_SOCK"]
    p = subprocess.run(shlex.split(transport) + [CAPTURE], capture_output=True, timeout=timeout, env=env)
    out = (p.stdout + p.stderr).decode(errors="replace").replace("\r", "")
    if "=== PIDIN1 ===" not in out or "=== END ===" not in out.rsplit("=== ARGS ===", 1)[-1]:
        raise RuntimeError("capture did not finish on the target (no pidin output came back):\n" + out[-1500:])
    return out


def commands(text: str) -> dict[int, str]:
    """`pidin arg` → {pid: command line} for every process."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s+(\S.*?)\s*$", line)
        if m:
            out[int(m[1])] = m[2]
    return out


def involved(j: dict) -> list[int]:
    if j["kind"] == "deadlock":
        return [m["pid"] for c in j["cycles"] for m in c] + [b["pid"] for b in j["behind"]]
    if j["kind"] == "priority_chain":
        return [x for c in j["chains"] for x in (c["waiter"]["pid"], c["server"]["pid"])]
    if j["kind"] == "missing_reply":
        return [x for w in j["waits"] for x in (w["waiter"]["pid"], w["server"]["pid"])]
    return []


def call_sites(src: str, cmdlines: list[str]) -> list[str]:
    """`file:line: text` of message-passing calls in C files named like a binary of an involved process."""
    bins = {os.path.basename(c.split()[0]) for c in cmdlines if c}
    hits = []
    for d, _, files in os.walk(src):
        for f in sorted(files):
            if f.endswith(".c") and f[:-2] in bins:
                p = os.path.join(d, f)
                for n, line in enumerate(open(p, errors="replace"), 1):
                    if CALLS.search(line):
                        hits.append(f"{os.path.relpath(p, src)}:{n}: {line.strip()}")
    return hits


def check(out: str, focus=None, src=None) -> dict:
    """Pure: captured text → verdict, with command lines and (optionally) source call sites."""
    first = wg.parse(section(out, "PIDIN1"))
    later = [wg.parse(section(out, k)) for k in ("PIDIN2", "PIDIN3")]
    j = wg.judge(first, focus, later)
    args = commands(section(out, "ARGS"))
    pids = involved(j)
    who = {p: args.get(p, "?") for p in dict.fromkeys(pids)}
    return {"kind": j["kind"], "judge": j, "graph": wg.describe(j), "commands": who, "threads": len(first),
            "sites": call_sites(src, list(who.values())) if src and pids else []}


def report(r: dict) -> str:
    lines = [r["graph"]]
    for p, c in r["commands"].items():
        lines.append(f"  pid {p}: {c}")
    if r["sites"]:
        lines.append("message-passing calls in the matching sources (places to look, not a proof):")
        lines += [f"  {s}" for s in r["sites"]]
    return "\n".join(lines)
