"""«Same message structure» check: a hang fix must keep who talks to whom (pure, no AI, no target).

Why (2026-11-16): on the first held-out run 7 of the naive baseline's 12 «fixes» rewired run.sh or made one ring
member stop sending. The rerun was alive, so a liveness-only verifier called them solved. A fix is a QNX fix only if
the program still does what it did: the same processes, and every pair that exchanged messages still exchanges them.

Inputs come from one boot (check.sh → snap): `pidin arg` (pid → command line) and the qd_trace records
(common/qd_trace.c, linked into every program): "<pid> <S|R> <M|P> <peer pid> <attempts> <done>".
Processes are matched across the two boots by command line, never by pid (pids differ per boot).

Rules, checked by `compare(before, after)`:
  1. same set of program processes (by command line) — none gone, none added, run.sh wiring unchanged at runtime;
  2. every pair (sender → receiver) that tried to send before the fix has, after it, at least MIN_DONE completed
     sends (MsgSend returned = the receiver replied; pulse delivered) AND, if the receiver reads its channel at all
     in the rerun, it counted at least MIN_DONE arrivals from that sender (message or pulse). A pulse instead of a
     synchronous send is fine; no send is not. A receiver that never calls a receive (a client that only attached
     a name, like the v1 generator's starter) cannot count arrivals; such pulses are kept as `unread` pairs
     (2026-11-16, set after the v1 re-judge showed it, before the v2 held-out run). Removing receive calls from the
     source to get there is rejected statically (`receive_removed`);
  3. no thread removed from any program process;
  4. a process that took no part in messaging before (a CPU load, say) keeps its threads' priorities and stays busy
     where it was busy (lowering or idling the load is not a fix of the program).
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
ESCAPE = re.compile(r"__wrap_|__real_|\basm\b|__asm|__kercall|\bdlsym\b|\bdlopen\b|\bsyscall\b|_syspage_ptr")


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
        m = re.match(r"\s*(\d+)\s+([SRW])\s+([MPCE])\s+(\d+)\s+(\d+)\s+(\d+)\s*$", line)
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


def build(args: dict[int, str], msgs: list[tuple], threads) -> dict:
    """One boot → {"procs": [...], "pairs": {"a -> b": {...}}, "threads": {ident: [[prio, busy], ...]}}."""
    ids = idents(args)
    pairs = {}
    receivers = sorted({ids[m[0]] for m in msgs if m[1] == "W" and m[0] in ids})

    def pair(src, dst):
        return pairs.setdefault(f"{ids[src]} -> {ids[dst]}", {"att": 0, "done": 0, "recv": 0, "kinds": []})

    for pid, d, kind, peer, att, done in msgs:
        if d == "W":
            continue
        if pid not in ids or peer not in ids or pid == peer:
            continue  # system servers (procnto, devb, ...) and self: not a pair of the program
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
    return {"procs": sorted(ids.values()), "pairs": pairs, "receivers": receivers, "threads": {k: sorted(v, key=str) for k, v in th.items()}}


def _talkers(pairs) -> set[str]:
    return {x for k, v in pairs.items() if v["att"] or v["recv"] for x in k.split(" -> ")}


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
    for k, v in sorted(before["pairs"].items()):
        if not v["att"]:
            continue
        a = after["pairs"].get(k, {"done": 0, "recv": 0})
        reads = k.split(" -> ")[1] in after.get("receivers", []) or "receivers" not in after
        if "E" in a.get("kinds", []):  # MsgDeliverEvent: the pulse comes on the client's own connection, sender unnamed
            reads = False
        if a["done"] < MIN_DONE or (reads and a["recv"] < MIN_DONE):
            why.append(f"pair no longer exchanges messages: {k} (after the fix: {a['done']} completed sends, "
                       f"{a['recv']} received; need {MIN_DONE} each)")
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


RECV = re.compile(r"\b(?:MsgReceive\w*|qd_receive)\s*\(")


def receive_removed(before: str, after: str) -> bool:
    """A fix must not take receive calls out of a source file (that would silence a receiver, see rule 2)."""
    return len(RECV.findall(after)) < len(RECV.findall(before))


def unread(before: dict, after: dict) -> list[str]:
    """Pairs whose sends complete but whose receiver never reads its channel (reported, not rejected)."""
    if not before or not after:
        return []
    return [k for k, v in sorted(before["pairs"].items()) if v["att"] and k.split(" -> ")[1] not in after.get("receivers", [])]


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
