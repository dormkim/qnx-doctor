"""Wait-for graph from a QNX `pidin` snapshot, judged by code (no AI).

pidin default columns: pid tid name prio STATE Blocked. For SEND and REPLY the Blocked column is the
peer *process* id (the server we sent to / are waiting for a reply from). pid 1 is procnto (kernel
services), so edges to pid 1 are not application waits and are left out.

Findings:
  deadlock        a cycle of processes, each SEND/REPLY-blocked on the next (members + who waits behind them)
  priority_chain  a thread waits (SEND/REPLY) on a READY server whose priority is below its own while a
                  thread of middle priority is RUNNING or READY — the server can not get the CPU (priority
                  inversion). READY counts: a runnable middle thread always goes before the server; at the
                  snapshot instant it may be off the CPU only because the observer itself (pidin, procnto at 63,
                  the serial driver printing) holds it (dev seed 1014, 2026-11-16).
  none            neither; long waits on a sleeping server or idle RECEIVE are normal
"""
import re
from dataclasses import dataclass

LINE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\S+)\s+(?:(\d+)([a-z])\s+)?([A-Z?]+)\s*(\d+)?\s*$")
WAIT = ("SEND", "REPLY")
RUNNABLE = ("RUNNING", "READY")


@dataclass(frozen=True)
class Thread:
    pid: int
    tid: int
    name: str
    prio: int | None
    state: str
    blocked: int | None


def parse(text: str) -> list[Thread]:
    """Threads from the first pidin table in `text` (later repeats of the same pid/tid are ignored)."""
    seen, out = set(), []
    for line in text.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        pid, tid = int(m[1]), int(m[2])
        if (pid, tid) in seen:
            continue
        seen.add((pid, tid))
        out.append(Thread(pid, tid, m[3], int(m[4]) if m[4] else None, m[6], int(m[7]) if m[7] else None))
    return out


def edges(threads) -> list[tuple[Thread, int]]:
    """(waiting thread, peer pid) for every SEND/REPLY wait on another application process."""
    return [(t, t.blocked) for t in threads
            if t.state in WAIT and t.blocked is not None and t.blocked > 1 and t.blocked != t.pid]


def cycles(threads) -> list[list[int]]:
    """Simple cycles in the process-level wait graph, each rotated to start at its smallest pid."""
    g: dict[int, set[int]] = {}
    for t, peer in edges(threads):
        g.setdefault(t.pid, set()).add(peer)
    found = set()

    def walk(start, node, path):
        for nxt in sorted(g.get(node, ())):
            if nxt == start:
                found.add(tuple(path))
            elif nxt not in path and nxt > start:  # only extend through larger pids: each cycle found once
                walk(start, nxt, path + [nxt])

    for s in sorted(g):
        walk(s, s, [s])
    return [list(c) for c in sorted(found)]


def behind(threads, members) -> list[Thread]:
    """Threads outside the cycle that wait (directly or through others) on a cycle member."""
    stuck, out, grew = set(members), [], True
    while grew:
        grew = False
        for t, peer in edges(threads):
            if peer in stuck and t.pid not in stuck:
                stuck.add(t.pid); out.append(t); grew = True
    return out


def inversions(threads) -> list[dict]:
    """High-priority waiter → READY low-priority server, with a runnable (RUNNING/READY) thread of priority in between."""
    by_pid: dict[int, list[Thread]] = {}
    for t in threads:
        by_pid.setdefault(t.pid, []).append(t)
    out = []
    for w, peer in edges(threads):
        if w.prio is None:
            continue
        for s in by_pid.get(peer, []):
            if s.state != "READY" or s.prio is None or s.prio >= w.prio:
                continue
            mid = [r for r in threads if r.state in RUNNABLE and r.prio is not None and s.prio < r.prio < w.prio
                   and r.pid not in (w.pid, s.pid)]
            if mid:
                out.append({"waiter": w, "server": s, "running": mid})
    return out


def _focus(threads, focus):
    """Keep findings that involve `focus` (pid or name substring); None keeps all."""
    if focus is None:
        return lambda pids: True
    if str(focus).isdigit():
        return lambda pids: int(focus) in pids
    hit = {t.pid for t in threads if str(focus) in t.name}
    return lambda pids: bool(hit & set(pids))


def judge(threads, focus=None) -> dict:
    keep = _focus(threads, focus)
    names = {t.pid: t.name for t in threads}
    state = {}
    for t, peer in edges(threads):
        state.setdefault(t.pid, f"{t.state}-blocked on {peer}")
    cyc = [c for c in cycles(threads) if keep(c)]
    if cyc:
        return {"kind": "deadlock",
                "cycles": [[{"pid": p, "name": names.get(p, "?"), "state": state.get(p)} for p in c] for c in cyc],
                "behind": [{"pid": t.pid, "name": t.name, "state": f"{t.state}-blocked on {t.blocked}"}
                           for t in behind(threads, {p for c in cyc for p in c})]}
    inv = [i for i in inversions(threads) if keep([i["waiter"].pid, i["server"].pid])]
    if inv:
        return {"kind": "priority_chain", "chains": [
            {"waiter": {"pid": i["waiter"].pid, "name": i["waiter"].name, "prio": i["waiter"].prio, "state": i["waiter"].state},
             "server": {"pid": i["server"].pid, "name": i["server"].name, "prio": i["server"].prio, "state": "READY"},
             "running": sorted({(r.pid, r.name, r.prio) for r in i["running"]})} for i in inv]}
    return {"kind": "none"}


def describe(j: dict) -> str:
    """One readable paragraph for the timeline and the AI prompt."""
    if j["kind"] == "deadlock":
        parts = []
        for c in j["cycles"]:
            parts.append(" -> ".join(f"{m['pid']}({m['name']}, {m['state']})" for m in c) + f" -> {c[0]['pid']}")
        if j["behind"]:
            parts.append("waiting behind the cycle: " + ", ".join(f"{b['pid']}({b['name']}, {b['state']})" for b in j["behind"]))
        return "DEADLOCK: " + "; ".join(parts)
    if j["kind"] == "priority_chain":
        parts = []
        for c in j["chains"]:
            w, s = c["waiter"], c["server"]
            run = ", ".join(f"{p}({n}) prio {q}" for p, n, q in c["running"])
            parts.append(f"{w['pid']}({w['name']}) prio {w['prio']} {w['state']}-blocked on {s['pid']}({s['name']}) "
                         f"which is READY at prio {s['prio']} while {run} is runnable (RUNNING/READY)")
        return "PRIORITY CHAIN: " + "; ".join(parts)
    return "no wait cycle and no priority chain"


def split_check(out: str) -> tuple[str, dict[str, int]]:
    """check.sh output → (pidin text, {role log: TICK count})."""
    pid = out.split("=== PIDIN ===", 1)[-1].split("=== TICKS ===", 1)[0]
    ticks = {}
    tail = out.split("=== TICKS ===", 1)[1] if "=== TICKS ===" in out else ""
    for line in tail.splitlines():
        m = re.match(r"\s*/tmp/(\S+)\.log\s+(\d+)\s*$", line)
        if m:
            ticks[m[1]] = int(m[2])
    return pid, ticks
