"""Reproducibility check, part 2 (2026-11-21, before sealed v6): does the UNMODIFIED run show what the label describes?

`repro_v3.py` only asks «did the loops stop or tick as the label expects». On the dev sets that let two kinds of
scenario through that never built the situation their label describes:
  - v4 D08, D13, D20, D23: the label says a client is REPLY-blocked on the server; in the recorded pidin lines no
    program thread was in REPLY (the client had not connected), yet «stops» was true;
  - v5 E04: run.sh starts four processes, three were in the process list, and no program thread was in REPLY.
Such a scenario is a harness failure, not a test of any arm. Two checks, per scenario, on the pidin snapshots:
  1. every program process run.sh starts in the background is in the process list;
  2. every thread state the label's `states` text names (SEND, REPLY, MUTEX, CONDVAR, SEM, JOIN, NANOSLEEP ...) is
     the state of at least one thread of the scenario's own processes, in at least one snapshot. RUNNING and READY
     count as one (a snapshot shows either). A «healthy» label is checked for processes only (its states pass by).
The check is per scenario, not per role: a role log name does not always name a process. It reads state words only
and judges nothing: no wait graph, no kind. It prints the label's own words that were not seen, so the author can
repair the scenario before the seal. States only, no timing (QNX licence 4.6(i)).

  python3 bench/repro_states.py --labels LABELS.json --pool POOL --code runs/x_code.jsonl     # from a recorded AI-off run
`repro_v3.py --same-boot` runs the same check on the boot it makes anyway.
A recorded run does not always hold every program line (see from_record); a state missing from such a record is
printed as «CHECK BY HAND», not as a failure. The boot made by repro_v3.py has all lines.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qnx_doctor import waitgraph as wg  # noqa: E402

RUNNABLE = ("RUNNING", "READY")
WORDS = ("SEND", "REPLY", "RECEIVE", "MUTEX", "CONDVAR", "SEM", "JOIN", "NANOSLEEP", "SIGWAITINFO", "SIGSUSPEND",
         "WAITTHREAD", "WAITPAGE", "WAITCTX", "RWLOCK", "STOPPED", "NET_SEND", "NET_REPLY") + RUNNABLE


NEGATED = re.compile(r"\b(?:no|not|never|without|neither|nor)\b[^;,.:()]*")


def named_states(label) -> list[tuple[str, ...]]:
    """Thread states the label's `states` text says are there (a string in v3, {role: text} since v4). Each entry is
    a tuple of alternatives: «SEND/REPLY-blocked» is one entry (SEND, REPLY); RUNNING and READY are always one entry.
    A clause that starts with no/not/never/without («no SEND/REPLY edge») names nothing."""
    st = label.get("states") or ""
    text = NEGATED.sub(" ", " ; ".join(st.values()) if isinstance(st, dict) else str(st))
    out = set()
    for group in re.findall(r"[A-Z][A-Z_]{2,}(?:/[A-Z][A-Z_]{2,})*", text):
        alt = tuple(sorted({w for w in group.split("/") if w in WORDS}))
        if alt:
            out.add(RUNNABLE if set(alt) & set(RUNNABLE) else alt)
    return sorted(out)


def started(run_sh: str, sid: str) -> int:
    """Program processes run.sh starts in the background (/var/qd/<sid>/<prog> ... &)."""
    return len(re.findall(rf"^\s*/var/qd/{re.escape(sid)}/\S+.*&\s*$", run_sh, flags=re.M))


def seen_states(snaps, sid: str) -> set[str]:
    out = set()
    for th in snaps:
        for t in th:
            if f"var/qd/{sid}/" in t.name:
                out.add(t.state)
    return out


def check(label, sid: str, run_sh: str, snaps, alive=None, partial=False) -> list[str]:
    """Reasons the unmodified run does not show the label's situation; [] = it does. `alive`: process count if it was
    recorded apart from the lines; `partial`: the snapshots hold only some of the program's lines (recorded run)."""
    why = []
    n = started(run_sh, sid)
    have = alive if alive is not None else len({t.pid for th in snaps[:1] for t in th if f"var/qd/{sid}/" in t.name})
    if have < n:
        why.append(f"run.sh starts {n} program processes, {have} in the process list")
    if label.get("kind") in ("healthy", "none"):
        return why
    seen = seen_states(snaps, sid)
    for alt in named_states(label):
        if not set(alt) & seen:
            w = "/".join(alt)
            why.append(f"label names a thread in {w}; no program thread was in {w}" + (f" {PARTIAL}" if partial else ""))
    return why


PARTIAL = "(the record does not hold every program line: check by hand)"


def from_record(row, sid: str):
    """(snapshots, process count, partial) from one AI-off record. Lines: the graph entry's pidin lines of the first
    snapshot — only the judged processes when the code named a hang, none in records made before the lines of an
    unjudged program were kept, and (until 2026-11-21) no line of a thread whose Blocked column the strict parser
    dropped. Process count: the `pidin arg` list in the structure record when there is one, else the larger of the
    recorded `alive` and the pids in the lines."""
    g = [t for t in row.get("timeline", []) if t.get("kind") == "graph"]
    if not g:
        return None
    th = wg.parse("\n".join(g[0].get("lines") or []), any_blocked=True)
    pids = {t.pid for t in th if f"var/qd/{sid}/" in t.name}
    procs = (g[0].get("structure") or {}).get("procs")
    n = len(procs) if procs is not None else max(g[0].get("alive") or 0, len(pids))
    return [th], n, g[0].get("verdict") != "none" or len(pids) < n


def main():
    ap = argparse.ArgumentParser()
    for f in ("--labels", "--pool", "--code"):
        ap.add_argument(f, required=True)
    a = ap.parse_args()
    labels = {k: v for k, v in json.load(open(a.labels)).items() if not k.startswith("_")}
    rows = {json.loads(l)["id"]: json.loads(l) for l in open(a.code)}
    bad = hand = 0
    for sid in sorted(labels):
        rec = from_record(rows.get(sid, {}), sid)
        if rec is None:
            print(sid, "NO RECORD"); bad += 1
            continue
        why = check(labels[sid], sid, open(os.path.join(a.pool, sid, "run.sh")).read(), *rec)
        unsure = bool(why) and all(w.endswith(PARTIAL) for w in why)
        bad += bool(why) and not unsure
        hand += unsure
        print(sid, "ok" if not why else ("CHECK BY HAND: " if unsure else "NOT SHOWN: ") + "; ".join(why))
    print(f"{len(labels) - bad - hand}/{len(labels)} show the label's situation, {bad} do not, {hand} need a look by hand")


if __name__ == "__main__":
    main()
