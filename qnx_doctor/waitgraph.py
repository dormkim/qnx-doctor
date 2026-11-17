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
  missing_reply   a thread is REPLY-blocked on an application process whose threads are ALL RECEIVE-blocked: the
                  server took the message and went back to its channel without replying (a code path that forgets
                  MsgReply). Added 2026-11-17 for the QNX trap scenarios (dev pool). System processes (proc/boot/,
                  system/) are left out: a resource manager holding a blocked read is normal.
  none            neither; long waits on a sleeping server or idle RECEIVE are normal
"""
import re
from dataclasses import dataclass

LINE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\S+)\s+(?:(\d+)([a-z])\s+)?([A-Z?]+)\s*(\d+)?\s*$")
# Any Blocked column (SEM, CONDVAR, MUTEX show an address there). Only progress.classify reads these threads, to say
# where a stopped loop waits (harness check bo01, 2026-11-17); the judge keeps LINE, so its findings are unchanged.
LINE_ANY = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\S+)\s+(?:(\d+)([a-z])\s+)?([A-Z?]+)(?:\s+(\S+))?\s*$")
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


def parse(text: str, any_blocked: bool = False) -> list[Thread]:
    """Threads from the first pidin table in `text` (later repeats of the same pid/tid are ignored). `any_blocked`
    also keeps threads whose Blocked column is not a pid (blocked = None for those)."""
    seen, out = set(), []
    for line in text.splitlines():
        m = (LINE_ANY if any_blocked else LINE).match(line)
        if not m:
            continue
        pid, tid = int(m[1]), int(m[2])
        if (pid, tid) in seen:
            continue
        seen.add((pid, tid))
        out.append(Thread(pid, tid, m[3], int(m[4]) if m[4] else None, m[6], int(m[7]) if m[7] and m[7].isdigit() else None))
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


SYSTEM = ("proc/boot/", "/proc/boot/", "system/", "/system/")


def missing_replies(threads) -> list[dict]:
    """REPLY-blocked waiter on an application process that is idle on its channel(s): nobody will ever reply."""
    by_pid: dict[int, list[Thread]] = {}
    for t in threads:
        by_pid.setdefault(t.pid, []).append(t)
    out = []
    for w, peer in edges(threads):
        srv = by_pid.get(peer, [])
        if w.state != "REPLY" or not srv or w.name.startswith(SYSTEM) or srv[0].name.startswith(SYSTEM):
            continue
        if all(t.state == "RECEIVE" for t in srv):
            out.append({"waiter": w, "server": srv[0]})
    return out


def _focus(threads, focus):
    """Keep findings that involve `focus` (pid or name substring); None keeps all."""
    if focus is None:
        return lambda pids: True
    if str(focus).isdigit():
        return lambda pids: int(focus) in pids
    hit = {t.pid for t in threads if str(focus) in t.name}
    return lambda pids: bool(hit & set(pids))


def _pair(i) -> tuple[int, int]:
    return i["waiter"].pid, i["server"].pid


def _persists(found, later, finder):
    """Keep only findings whose (waiter, server) pair is found again in every later snapshot."""
    for th in later:
        again = {_pair(i) for i in finder(th)}
        found = [i for i in found if _pair(i) in again]
    return found


def judge(threads, focus=None, later=(), moving=frozenset()) -> dict:
    """`later`: further pidin snapshots of the same boot, taken a moment after the first (snap.c, 2026-11-17). A
    priority chain or a missing reply counts only if the same waiter → server pair is there in every snapshot.
    `moving`: pids whose loop's TICK count grew between the two counts of the same boot (progress.py). A chain or a
    missing reply whose waiter is one of them is a slow wait, not a hang, and is dropped (2026-11-17, before sealed
    v4: a server that answers on every timer pulse looks like a lost reply in all three snapshots; v3 q19).
    Why: one snapshot catches passing states. After a ring was fixed (v2 held-out, naive arm, 2 cases) a ring member
    or the serial driver was runnable for an instant while the fixed-priority server was busy with a request, and the
    rerun was judged «chain». A real chain (a CPU load holding the server down) is still there a moment later; a
    passing one is not. A cycle cannot clear by itself, so deadlocks are judged on the first snapshot."""
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
    stuck = lambda i: keep([i["waiter"].pid, i["server"].pid]) and i["waiter"].pid not in moving  # noqa: E731
    inv = _persists([i for i in inversions(threads) if stuck(i)], later, inversions)
    if inv:
        return {"kind": "priority_chain", "chains": [
            {"waiter": {"pid": i["waiter"].pid, "name": i["waiter"].name, "prio": i["waiter"].prio, "state": i["waiter"].state},
             "server": {"pid": i["server"].pid, "name": i["server"].name, "prio": i["server"].prio, "state": "READY"},
             "running": sorted({(r.pid, r.name, r.prio) for r in i["running"]})} for i in inv]}
    lost = _persists([i for i in missing_replies(threads) if stuck(i)], later, missing_replies)
    if lost:
        return {"kind": "missing_reply", "waits": [
            {"waiter": {"pid": i["waiter"].pid, "name": i["waiter"].name}, "server": {"pid": i["server"].pid, "name": i["server"].name}}
            for i in lost]}
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
    if j["kind"] == "missing_reply":
        return "MISSING REPLY: " + "; ".join(
            f"{w['waiter']['pid']}({w['waiter']['name']}) REPLY-blocked on {w['server']['pid']}({w['server']['name']}), "
            f"whose threads are all RECEIVE-blocked (it took the message and never replied)" for w in j["waits"])
    return "no wait cycle and no priority chain"


def split_check(out: str) -> tuple[str, dict[str, int]]:
    """check.sh output → (pidin text, {role log: TICK count})."""
    pid = out.split("=== PIDIN ===", 1)[-1].split("=== TICKS ===", 1)[0]
    return pid, tick_counts(out)


def tick_counts(out: str, section: str = "TICKS") -> dict[str, int] | None:
    """{role log: TICK count} of one snap section (TICKS = first count, TICKS2 = the second, snap.c 2026-11-17).
    Stops at the next «=== » header, so a later section is never read into an earlier one. None if the section is
    absent (older recordings have no TICKS2); {} if it is there but empty."""
    if f"=== {section} ===" not in out:
        return None if section != "TICKS" else {}
    ticks = {}
    tail = out.split(f"=== {section} ===", 1)[1].split("\n=== ", 1)[0]
    for line in tail.splitlines():
        m = re.match(r"\s*/tmp/(\S+)\.log\s+(\d+)\s*$", line)
        if m:
            ticks[m[1]] = int(m[2])
    return ticks
