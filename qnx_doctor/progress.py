"""Liveness by progress: did each loop's TICK count grow between two counts of the same boot (snap.c TICKS, TICKS2)?

Why (2026-11-17, before sealed v4; docs/분석_sealed3_1117.md J1): the judge used to decide from thread states only,
and `healthy` was «no finding and TICK total > 0». Two v3 failures came from that one root:
  - a server that answers on every timer pulse: its client is REPLY-blocked on a RECEIVE-blocked server in all three
    snapshots (looks like a lost reply) while the client keeps ticking -> was called missing_reply (v3 q19);
  - a loop that ticked a few times and then spun on the CPU: no finding, TICK total > 0 -> was called healthy (v3 q11).
Now: a waiter whose loop grew is not hung (waitgraph.judge `moving`), healthy needs growth, and a stop that the wait
graph cannot name is reported as such: spinning on the CPU, blocked in a non-message state, or not enough
information. Pure functions over parsed data; hang.observe feeds them.

Role ↔ process: a role log is /tmp/d0<role>.log and a program is /var/qd/<scenario>/<prog>; they match when <role> is
<prog> (the scenario format). A role that matches no process is still counted for «healthy», not for a waiter.
"""
from .waitgraph import RUNNABLE

GREW, FLAT, IDLE, GONE = "grew", "flat", "idle", "missing"  # idle = 0 both times (a log that never ticks)
MESSAGE_STATES = ("SEND", "REPLY", "RECEIVE")


def moves(first: dict, second: dict | None) -> dict[str, str] | None:
    """{role: grew | flat | idle | missing}; None when there is no second count (older harness, --live)."""
    if second is None:
        return None
    out = {}
    for role, a in first.items():
        b = second.get(role)
        out[role] = GONE if b is None else GREW if b > a else IDLE if a == 0 and b == 0 else FLAT
    return out


def _prog(t):
    return t.name.rstrip("/").split("/")[-1]


def programs(threads, name: str) -> dict[int, str]:
    """{pid: program name} of the scenario's own processes (/var/qd/<name>/<prog>)."""
    return {t.pid: _prog(t) for t in threads if f"var/qd/{name}/" in t.name}


def role_pids(threads, name: str, roles) -> dict[str, set[int]]:
    """{role: pids of the program with the same name}. d0<role> → <role>."""
    progs = programs(threads, name)
    out = {}
    for r in roles:
        key = r[2:] if r.startswith("d0") else r
        out[r] = {p for p, n in progs.items() if n == key}
    return out


def moving_pids(threads, name, mv) -> frozenset[int]:
    if not mv:
        return frozenset()
    rp = role_pids(threads, name, mv)
    return frozenset(p for r, s in mv.items() if s == GREW for p in rp.get(r, ()))


def _spinning(pids, snaps) -> list[int]:
    """Pids with a thread RUNNING/READY in every snapshot (a CPU loop, not a wait)."""
    out = []
    for p in sorted(pids):
        if all(any(t.pid == p and t.state in RUNNABLE for t in th) for th in snaps):
            out.append(p)
    return out


def classify(kind: str, threads, later, name: str, ticks: dict, mv: dict | None) -> dict:
    """-> {state, why, roles}. state: hang (the wait graph named one) | healthy | spinning | blocked_other | no_info.
    Without a second count (mv None) the old rule stays: healthy = no finding and TICK total > 0."""
    if kind != "none":
        return {"state": "hang", "why": "", "roles": mv}
    if mv is None:
        if sum(ticks.values()) > 0:
            return {"state": "healthy", "why": "no second TICK count; some loop ticked", "roles": None}
    else:
        stalled = [r for r, s in mv.items() if s in (FLAT, GONE)]
        if any(s == GREW for s in mv.values()) and not stalled:
            return {"state": "healthy", "why": "every loop that ticked kept ticking", "roles": mv}
    progs = programs(threads, name)
    rp = role_pids(threads, name, mv or ticks)
    grown = {p for r, s in (mv or {}).items() if s == GREW for p in rp.get(r, ())}
    suspects = [p for p in progs if p not in grown]
    stalled = {p for r, s in (mv or {r: FLAT for r in ticks}).items() if s != GREW for p in rp.get(r, ())}
    snaps = [threads, *later]
    # A program whose own loop stalled first; any other program only if none of those spins (a CPU-load program
    # without a TICK log is busy by design and should not be named while the stalled loop is the one spinning).
    spin = _spinning([p for p in suspects if p in stalled], snaps) or _spinning(suspects, snaps)
    if spin:
        who = ", ".join(f"{p}({progs[p]})" for p in spin)
        return {"state": "spinning", "roles": mv,
                "why": f"not a message-passing hang: {who} is running on the CPU (RUNNING/READY in every snapshot) "
                       "while its loop does not tick"}
    other = sorted({(progs[t.pid], t.state) for th in snaps for t in th if t.pid in suspects
                    and t.state not in MESSAGE_STATES and t.state not in RUNNABLE})
    if other:
        return {"state": "blocked_other", "roles": mv,
                "why": "not a message-passing hang: loop stopped while blocked outside message passing ("
                       + ", ".join(f"{p} {s}" for p, s in other) + "); the cause is not in the wait graph"}
    return {"state": "no_info", "roles": mv,
            "why": "not enough information: loop stopped, but no wait cycle, priority chain, lost reply or CPU loop "
                   "was seen"}


def detected(state: str, kind: str) -> str:
    """What the tool names: a hang kind, «none» (healthy) or «unknown» (stopped, cause not named)."""
    if state == "hang":
        return kind
    return "none" if state == "healthy" else "unknown"
