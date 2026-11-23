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
from .waitgraph import RUNNABLE, self_sends

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
    """{role: pids of the program with the same name}. d0<role> → <role>. A role may also carry the scenario id in
    front of the program name (d0<id><prog>, as the v6 author wrote them; 2026-11-23, v7 plan section 2, after v6
    su9: the role never matched its program, so a loop that kept ticking still counted as a hung waiter). Failing an
    exact match, a role names the one program whose name starts with it (v6 euf: role map, program mapgen); with
    no such program, or more than one, the role matches nothing."""
    progs = programs(threads, name)
    out = {}
    for r in roles:
        key = r[2:] if r.startswith("d0") else r
        exact = {p for p, n in progs.items() if n == key or key == f"{name}{n}"}
        if not exact:
            short = key[len(name):] if key.startswith(name) and len(key) > len(name) else key
            names = {n for n in progs.values() if n.startswith(short)}
            exact = {p for p, n in progs.items() if n in names} if len(names) == 1 else set()
        out[r] = exact
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


def _waits(suspects, snaps, progs) -> str:
    """Waits outside message passing of the suspect programs, with pidin's Blocked column as printed (first snapshot
    that shows each thread). Added to every «unknown» reason (2026-11-21): a MUTEX wait used to be dropped by the
    parser, so the reason for dev set v4 D02/D10/D17 did not mention it. Shown, not interpreted: what the column means
    (for example whether a MUTEX line's last value is the thread that holds the lock) is not decided here."""
    seen, out = set(), []
    for th in snaps:
        for t in th:
            if t.pid in suspects and (t.pid, t.tid) not in seen and t.state not in MESSAGE_STATES and t.state not in RUNNABLE:
                seen.add((t.pid, t.tid))
                out.append(f"{progs[t.pid]} thread {t.tid} {t.state}" + (f" {t.detail}" if t.detail else ""))
    text = (" Waits outside message passing, as pidin printed them (not interpreted): " + "; ".join(out) + ".") if out else ""
    # A send to the thread's own process (dev set v4 D22). Shown like the waits above; not named a deadlock until a
    # new dev scenario has been checked on a target (2026-11-21).
    own = [f"{progs[t.pid]} thread {t.tid} SEND {t.blocked}" for p in self_sends(snaps[0], snaps[1:]) if p in suspects
           for t in snaps[0] if t.pid == p and t.state == "SEND" and t.blocked == p]
    if own:
        text += (" A thread is SEND-blocked on its own process and no thread of that process is RECEIVE-blocked, in "
                 "every snapshot (shown, not named): " + "; ".join(own) + ".")
    return text


def _loads(threads, later, name, mv, ticks) -> set[str]:
    """Roles that are CPU loads, not stopped loops (2026-11-23, after v6 euf and qsa; a heuristic, not measured on a
    sealed set). A role is a load when its log printed at most one TICK and then stayed flat, another role's loop grew,
    and a program of the scenario is on the CPU (RUNNING/READY) in every snapshot without any thread ever in a message
    state. When the role matches its program by name, that program itself must be the one on the CPU. A loop that
    ticked more than once and then stopped is not a load: a program that ticks and then spins stays «spinning»."""
    if not mv or not any(s == GREW for s in mv.values()):
        return set()
    snaps = [threads, *later]
    progs = programs(threads, name)
    quiet = lambda pids: not any(t.pid in pids and t.state in MESSAGE_STATES for th in snaps for t in th)  # noqa: E731
    rp = role_pids(threads, name, mv)
    grown = {p for r, s in mv.items() if s == GREW for p in rp.get(r, ())}
    busy_quiet = {p for p in _spinning([p for p in progs if p not in grown], snaps) if quiet({p})}
    out = set()
    for r, s in mv.items():
        if s != FLAT or ticks.get(r, 0) > 1:
            continue
        pids = rp.get(r) or set()
        if pids and set(_spinning(pids, snaps)) == pids and quiet(pids):
            out.add(r)
        elif not pids and busy_quiet:
            out.add(r)
    return out


def classify(kind: str, threads, later, name: str, ticks: dict, mv: dict | None) -> dict:
    """-> {state, why, roles}. state: hang (the wait graph named one) | healthy | spinning | blocked_other | no_info.
    Without a second count (mv None) the old rule stays: healthy = no finding and TICK total > 0."""
    loads = _loads(threads, later, name, mv, ticks)
    if mv is not None:
        stalled = [r for r, s in mv.items() if s in (FLAT, GONE) and r not in loads]
        if any(s == GREW for s in mv.values()) and not stalled:
            # Progress first (2026-11-23, v7 plan section 2, after v6 su9, euf, qsa): when every loop that ticked
            # kept ticking, no wait in a snapshot makes the program hung, and a CPU load outside messaging that
            # printed a TICK once is not a stopped loop.
            why = "every loop that ticked kept ticking"
            if kind != "none":
                why += f" (the snapshots alone looked like {kind.replace('_', ' ')})"
            if loads:
                why += "; " + ", ".join(sorted(loads)) + " busy on the CPU outside message passing (a load)"
            return {"state": "healthy", "why": why, "roles": mv}
    if kind != "none":
        return {"state": "hang", "why": "", "roles": mv}
    if mv is None:
        if sum(ticks.values()) > 0:
            return {"state": "healthy", "why": "no second TICK count; some loop ticked", "roles": None}
    progs = programs(threads, name)
    rp = role_pids(threads, name, mv or ticks)
    grown = {p for r, s in (mv or {}).items() if s == GREW for p in rp.get(r, ())}
    suspects = [p for p in progs if p not in grown]
    stalled = {p for r, s in (mv or {r: FLAT for r in ticks}).items() if s != GREW for p in rp.get(r, ())}
    snaps = [threads, *later]
    waits = _waits(suspects, snaps, progs)
    # A program whose own loop stalled first; any other program only if none of those spins (a CPU-load program
    # without a TICK log is busy by design and should not be named while the stalled loop is the one spinning).
    spin = _spinning([p for p in suspects if p in stalled], snaps) or _spinning(suspects, snaps)
    if spin:
        who = ", ".join(f"{p}({progs[p]})" for p in spin)
        return {"state": "spinning", "roles": mv,
                "why": f"not a message-passing hang: {who} is running on the CPU (RUNNING/READY in every snapshot) "
                       "while its loop does not tick." + waits}
    other = sorted({(progs[t.pid], t.state) for th in snaps for t in th if t.pid in suspects
                    and t.state not in MESSAGE_STATES and t.state not in RUNNABLE})
    if other:
        return {"state": "blocked_other", "roles": mv,
                "why": "not a message-passing hang: loop stopped while blocked outside message passing ("
                       + ", ".join(f"{p} {s}" for p, s in other) + "); the cause is not in the wait graph." + waits}
    return {"state": "no_info", "roles": mv,
            "why": "not enough information: loop stopped, but no wait cycle, priority chain, lost reply or CPU loop "
                   "was seen." + waits}


def detected(state: str, kind: str) -> str:
    """What the tool names: a hang kind, «none» (healthy) or «unknown» (stopped, cause not named)."""
    if state == "hang":
        return kind
    return "none" if state == "healthy" else "unknown"
