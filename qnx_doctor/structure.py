"""«Same message structure» check: a hang fix must keep who talks to whom (pure, no AI, no target).

Why (2026-11-16): on the first held-out run 7 of the naive baseline's 12 «fixes» rewired run.sh or made one ring
member stop sending. The rerun was alive, so a liveness-only verifier called them solved. A fix is a QNX fix only if
the program still does what it did: the same processes, and every pair that exchanged messages still exchanges them.

Inputs come from one boot (check.sh → snap): `pidin arg` (pid → command line) and the qd_trace records
(common/qd_trace.c, linked into every program): "<pid> <S|R> <M|P|E> <peer pid> <attempts> <done>", plus
"<pid> W C ..." (the process calls a receive) and "<pid> G E <server pid> ..." (it registered a pulse event for that
server: MsgRegisterEvent).
Processes are matched across the two boots by command line, never by pid (pids differ per boot).

Rules, checked by `compare(before, after)`:
  1. same set of program processes (by command line) — none gone, none added, run.sh wiring unchanged at runtime;
  2. every pair (sender → receiver) that tried to send before the fix has, after it, at least MIN_DONE completed
     sends (MsgSend returned = the receiver replied; pulse delivered) AND, if the receiver reads its channel at all
     in the rerun, it counted at least MIN_DONE arrivals from that sender (message or pulse). A pulse instead of a
     synchronous send is fine; no send is not. Since 2026-11-22 the records are read twice in the rerun (`recount`):
     every such pair must also have completed sends AND arrivals between the two readings, so an exchange that
     stops after a few rounds is not a fix, and neither is a pulse that nobody is seen to read. A process that
     sends to itself is a pair like any other. The exceptions described next apply to older recordings only
     (no `recount`). A receiver that never calls a receive (a client that only attached
     a name, like the v1 generator's starter) cannot count arrivals; such pulses are kept as `unread` pairs
     (2026-11-16, set after the v1 re-judge showed it, before the v2 held-out run). Removing receive calls from the
     source to get there is rejected statically (`receive_removed`).
     MsgDeliverEvent (kind E, 2026-11-16, evening): the server names the client from the rcvid ("S E"), the client names the
     server from the event it registered ("G E") and counts each such pulse on its own connection ("R E"). A pair
     with E sends needs arrivals only if the client registered a pulse event for that server; a signal event cannot
     be counted at the client and is reported as `unread`, like a pulse to a process that never receives;
  3. no thread removed from any program process (counted over every thread since 2026-11-22);
  4. a process that took no part in messaging before (a CPU load, say) keeps its threads' priorities and stays busy
     where it was busy (lowering or idling the load is not a fix of the program);
  5. no fix is proven for a program that had a thread in a MUTEX wait in every snapshot of the hung observation
     (2026-11-22). Lock use is not recorded, so a corrected lock order and a deleted lock look the same here
     (harness check mx01). This keeps mutex hangs «not fixed» for every arm, on purpose and with that reason.
Static rules (run.sh and the harness common/ are not editable, no linker/syscall escape) are in `static_reject`.
"""
import re

MIN_DONE = 2
# Told to every arm that proposes a fix (ours and the naive baseline), so both know what «fixed» means.
RULES = ("The fix is checked on the target, not only for liveness: edit only the program's .c/.h files (run.sh and "
         "common/ are not editable); the same processes must run; every pair of processes that sent messages before "
         "must still send and receive messages after the fix (a pulse instead of a synchronous send is fine, no send "
         "is not); no thread may be removed; a process that takes no part in messaging (for example a CPU load) "
         "must keep its priorities and its load.")
RUNNABLE = ("RUNNING", "READY")
# a fix must not reach around the recorder (qd_trace.c is linked with --wrap) or the kernel-call layer
ESCAPE = re.compile(r"qdm\.|/dev/shmem/qd|__wrap_|__real_|\basm\b|__asm|__kercall|\bdlsym\b|\bdlopen\b|\bsyscall\b|_syspage_ptr")


def parse_args(text: str, name: str) -> dict[int, str]:
    """`pidin arg` → {pid: command line} for this program's processes (/var/qd/<name>/...)."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s+(\S.*?)\s*$", line)
        if m and m[2].startswith(f"/var/qd/{name}/"):
            out[int(m[1])] = m[2]
    return out


def parse_msgs(text: str) -> list[tuple]:
    """qd_trace lines → [(pid, dir, kind, peer, attempts, done)]."""
    out = []
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s+([SRWG])\s+([MPCE])\s+(\d+)\s+(\d+)\s+(\d+)\s*$", line)
        if m:
            out.append((int(m[1]), m[2], m[3], int(m[4]), int(m[5]), int(m[6])))
    return out


def idents(args: dict[int, str]) -> dict[int, str]:
    """pid → identity: the command line, with #k only if two processes share one."""
    seen, out = {}, {}
    for pid in sorted(args):
        k = seen.get(args[pid], 0)
        seen[args[pid]] = k + 1
        out[pid] = args[pid] + (f" #{k}" if k else "")
    return out


def build(args: dict[int, str], msgs: list[tuple], threads, later=()) -> dict:
    """One boot → {"procs": [...], "pairs": {"a -> b": {...}}, "threads": {ident: [[prio, busy], ...]},
    "lock_waits": [ident with a thread in MUTEX in this and every `later` snapshot]}."""
    ids = idents(args)
    pairs = {}
    receivers = sorted({ids[m[0]] for m in msgs if m[1] == "W" and m[0] in ids})

    def pair(src, dst):
        return pairs.setdefault(f"{ids[src]} -> {ids[dst]}", {"att": 0, "done": 0, "recv": 0, "kinds": [], "reg": False})

    for pid, d, kind, peer, att, done in msgs:
        if d == "W":
            continue
        if pid not in ids or peer not in ids:
            continue  # system servers (procnto, devb, ...): not a pair of the program. A process and itself is one.
        if d == "G":  # the client (pid) registered a pulse event that only this server (peer) may deliver
            pair(peer, pid)["reg"] = True
            continue
        p = pair(pid, peer) if d == "S" else pair(peer, pid)
        if d == "S":
            p["att"] += att; p["done"] += done
        else:
            p["recv"] += done
        if kind not in p["kinds"]:
            p["kinds"].append(kind)
    th = {}
    for t in threads:
        if t.pid in ids:
            th.setdefault(ids[t.pid], []).append([t.prio, t.state in RUNNABLE])
    stuck = {(t.pid, t.tid) for t in threads if t.state == "MUTEX" and t.pid in ids}
    for snap in later:
        stuck &= {(t.pid, t.tid) for t in snap if t.state == "MUTEX"}
    return {"procs": sorted(ids.values()), "pairs": pairs, "receivers": receivers,
            "lock_waits": sorted({ids[pid] for pid, _ in stuck}), "threads": {k: sorted(v, key=str) for k, v in th.items()}}


def recount(s: dict, args: dict[int, str], msgs1) -> dict:
    """Adds the first reading of the same boot's message records (snap.c MSGS1) to a structure built from the second:
    per pair, did completed sends and arrivals grow between the two. None = there was no first reading."""
    s["recount"] = msgs1 is not None
    if msgs1 is not None:
        early = build(args, msgs1, [])["pairs"]
        for k, v in s["pairs"].items():
            e = early.get(k, {"done": 0, "recv": 0})
            v["sending"], v["arriving"] = v["done"] > e["done"], v["recv"] > e["recv"]
    return s


def _talkers(pairs) -> set[str]:
    out = set()
    for k, v in pairs.items():
        src, dst = k.split(" -> ")
        # A process that only receives on its own connection (timer pulses) is not talking to anyone (rule 4).
        if v["att"] or (v["recv"] and src != dst):
            out |= {src, dst}
    return out


def compare(before: dict, after: dict) -> list[str]:
    """Reasons the fix changed the program's message structure; [] = same structure."""
    if not before or not after:
        return ["no message-structure record from one of the runs"]
    why = []
    gone = sorted(set(before["procs"]) - set(after["procs"]))
    new = sorted(set(after["procs"]) - set(before["procs"]))
    if gone:
        why.append("process gone or started differently: " + "; ".join(gone))
    if new:
        why.append("process not in the original program: " + "; ".join(new))
    for p in before.get("lock_waits", []):
        why.append(f"{UNPROVABLE} {p} had a thread waiting on a mutex in every snapshot, and lock use is not recorded")
    counted = "recount" in after  # absent in recordings older than 2026-11-22: judged as they were
    if counted and not after["recount"]:
        why.append(f"{UNPROVABLE} the message records of the rerun were not read a second time")
    for k, v in sorted(before["pairs"].items()):
        if not v["att"]:
            continue
        a = after["pairs"].get(k, {"done": 0, "recv": 0})
        reads = k.split(" -> ")[1] in after.get("receivers", []) or "receivers" not in after
        if _event_unread(a):  # signal event (or no registration seen): the client cannot count it
            reads = False
        if counted:  # nothing is taken as arrived unless it was seen arriving
            reads = True
        if a["done"] < MIN_DONE or (reads and a["recv"] < MIN_DONE):
            why.append(f"pair no longer exchanges messages: {k} (after the fix: {a['done']} completed sends, "
                       f"{a['recv']} received; need {MIN_DONE} each)")
        elif counted and after["recount"] and not (a.get("sending") and a.get("arriving")):
            why.append(f"pair stopped exchanging messages: {k} (no new "
                       f"{'arrivals' if a.get('sending') else 'completed sends'} between the rerun's two counts)")
    talk = _talkers(before["pairs"])
    for p, tb in sorted(before["threads"].items()):
        ta = after["threads"].get(p)
        if ta is None:
            continue  # already reported as gone
        if len(ta) < len(tb):
            why.append(f"thread removed: {p} had {len(tb)} threads, now {len(ta)}")
        elif p not in talk and sorted(map(str, ta)) != sorted(map(str, tb)):
            why.append(f"non-messaging process changed its threads' priority or load: {p} {tb} -> {ta}")
    return why


STATIC = "rejected (structure):"
UNPROVABLE = "fix cannot be proven:"


RECV = re.compile(r"\b(?:MsgReceive\w*|qd_receive)\s*\(")


def receive_removed(before: str, after: str) -> bool:
    """A fix must not take receive calls out of a source file (that would silence a receiver, see rule 2)."""
    return len(RECV.findall(after)) < len(RECV.findall(before))


def unread(before: dict, after: dict) -> list[str]:
    """Pairs whose sends complete but whose receiver never reads its channel (reported, not rejected)."""
    if not before or not after:
        return []
    return [k for k, v in sorted(before["pairs"].items())
            if v["att"] and (k.split(" -> ")[1] not in after.get("receivers", []) or _event_unread(after["pairs"].get(k, {})))]


def _event_unread(a: dict) -> bool:
    """MsgDeliverEvent sends whose client registered no pulse event for this server: arrivals cannot be counted."""
    return "E" in a.get("kinds", []) and not a.get("reg")


def static_reject(actions: list) -> str | None:
    """Edits that change the wiring or the harness, or escape the recorder. None = allowed to build."""
    for a in actions:
        path = str(a.get("path", "")).replace("\\", "/").lstrip("./")
        if path.endswith("run.sh") or path.endswith(".sh"):
            return f"rejected (structure): {path} starts the processes (the wiring); a fix must keep it unchanged"
        if path.startswith("common/") or "/common/" in path or path.split("/")[0] == "common":
            return f"rejected (structure): {path} is the observation harness, not the program"
        if not path.endswith((".c", ".h")):
            return f"rejected (structure): {path}: a hang fix edits the program's C sources only"
        if ESCAPE.search(str(a.get("replace", ""))):
            return f"rejected (structure): {path}: the replacement reaches around the message layer ({ESCAPE.search(str(a.get('replace'))).group(0)})"
    return None
