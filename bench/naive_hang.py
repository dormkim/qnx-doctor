"""Naive baseline for the hang doctor: the same model reads only what a developer has without qnx-doctor —
the program's source and its logs (TICK counts per role) — and guesses the cause and a fix in one reply (or, with --attempts 2, gets one more try after
seeing the rerun's TICK counts and the verifier's verdict, like our arm's retry, but never the wait graph).
No pidin snapshot, no wait graph, no docs search, no probes. Its fix (edit_file) goes through the same check
as ours: apply to a fresh copy → qcc → boot → rerun; «fixed» only if the rerun shows no cycle/chain and the
stopped loop ticks again. The answer key (labels.json) is never read here; bench/score_hang.py does that.

  python3 bench/naive_hang.py --pool DIR --code runs/x_code.jsonl --out runs/x_naive.jsonl
  python3 bench/naive_hang.py --pool DIR --code runs/x_code.jsonl --out runs/x_naive2.jsonl --attempts 2   # + same retries
`--code` = the AI-off run of the same scenarios; only its TICK counts are used (the logs a developer would see).
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qnx_doctor import hang  # noqa: E402
from qnx_doctor import structure as st  # noqa: E402
from qnx_doctor.hangdoctor import verdict  # noqa: E402

KINDS = ("deadlock", "priority_chain", "missing_reply", "none")
NAIVE_SYSTEM = """You are an experienced QNX 8.0 developer. A message-passing program was started on the target with
run.sh. You have its source files and its logs: for each role log, how many TICK lines it printed in the observation
window (a working loop prints TICK lines; 0 = that loop printed nothing). You have no other tools or observations.
Decide what is wrong. Reply with exactly ONE JSON object, nothing else:
  {"kind": "deadlock" | "priority_chain" | "missing_reply" | "none", "roles": ["role names involved"], "cause": "short cause",
   "actions": [{"type": "edit_file", "path": "relative path", "find": "exact text", "replace": "new text"}]}
kind: deadlock = processes wait on each other in a cycle of synchronous messages; priority_chain = a high-priority
client waits on a low-priority server that cannot get the CPU (priority inversion); missing_reply = a server received
a message on a code path that never replies, so its client waits forever; none = nothing is hung (long
waits can be normal). For none give no actions. Only edit_file actions, paths relative to the working directory,
`find` copied exactly from the file. Keep the program's intent; a timeout or sleep that only hides the wait is not a fix.
""" + st.RULES


def ask(context: str) -> dict:
    from anthropic import Anthropic
    from qnx_doctor.ai import MODEL, _json
    resp = Anthropic().messages.create(model=MODEL, max_tokens=4000, system=NAIVE_SYSTEM, thinking={"type": "adaptive"},
                                       messages=[{"role": "user", "content": context}])
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    try:
        out = _json(text)
    except Exception as e:  # an unreadable reply is a wrong answer, not a crash
        return {"kind": None, "error": f"no JSON: {e}", "actions": []}
    if out.get("kind") not in KINDS:
        out["error"] = f"kind not in {KINDS}: {out.get('kind')!r}"
    return out


def _feedback(res, v, err):
    """What a developer sees after trying a fix without qnx-doctor: whether it built, the TICK counts of the
    rerun and the verifier's verdict text. Never the wait graph or pidin lines (those are what our arm adds)."""
    if err:
        return err
    if not res.get("ok"):
        return f"{res.get('stage')} failed"
    state = ("fixed" if v["fixed"] else
             "came back alive but the message structure changed: " + "; ".join(v["structure"]) if v["live"] else
             "still hung")
    return f"{state}; TICK counts per role log after the rerun: {json.dumps(res.get('ticks'))}"


def _try(scen, sid, acts, ticks, alive, structure):
    fixed, err = hang.apply_fix(scen, acts)
    try:
        if err:
            return {"solved": False, "result": err, "static_reject": err.startswith(st.STATIC)}, _feedback(None, None, err)
        res = hang.observe(fixed, sid)
        v = verdict({"ticks": ticks, "alive": alive or 0, "structure": structure}, res)
        row = {"solved": v["fixed"], "live": v["live"], "structure_why": v["structure"], "unread": v["unread"],
               "result": "rerun: no cycle/chain, loop ticks again, same message structure" if v["fixed"] else
               "rejected: alive again but the message structure changed" if v["live"] else
               f"still hung: {res.get('graph') or res.get('stage') + ' failed'}"}
        return row, _feedback(res, v, None)
    finally:
        shutil.rmtree(fixed, ignore_errors=True)


def one(pool: str, sid: str, ticks: dict, alive, structure=None, attempts: int = 1) -> dict:
    """attempts=1 is the original one-shot baseline. attempts=2 is the «baseline + same retries» arm (2026-11-16,
    red team): the same number of tries as our arm, and after a failed try it is told what the rerun showed in
    the terms a developer has (TICK counts, verifier text), never the wait graph. So a difference between this arm
    and ours is what the pidin graph, the docs and the probes add, not the retry loop."""
    scen = os.path.join(pool, sid)
    work = hang.prepare(scen)
    base = [f"Program: {sid} (working directory {work})",
            "TICK counts per role log in the observation window: " + json.dumps(ticks),
            "Sources:\n" + hang.sources(work, sid)]
    shutil.rmtree(work, ignore_errors=True)
    tries, notes, g = [], [], {}
    for _ in range(attempts):
        g = ask("\n\n".join(base + notes))
        acts = g.get("actions") or []
        if g.get("kind") not in ("deadlock", "priority_chain", "missing_reply"):
            break  # «none» or unreadable: nothing to rerun
        if not acts:
            tries.append({"actions": [], "solved": False, "result": "no fix proposed"})
            break
        t, fb = _try(scen, sid, acts, ticks, alive, structure)
        tries.append({"actions": acts, **t})
        if t["solved"]:
            break
        notes.append(f"Already tried: {json.dumps(acts)} -> {fb}")
    row = {"id": sid, "mode": "naive" if attempts == 1 else f"naive_x{attempts}", "detected": g.get("kind"),
           "roles": g.get("roles"), "cause": g.get("cause"), "error": g.get("error"), "solved": None, "attempts": tries,
           "actions": tries[-1]["actions"] if tries else (g.get("actions") or [])}
    if tries:  # top-level fields = the last try (as before), first_solved = the first try alone
        row.update({k: v for k, v in tries[-1].items() if k != "actions"})
        row["solved"] = any(t["solved"] for t in tries)
        row["first_solved"] = tries[0]["solved"]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True); ap.add_argument("--code", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--attempts", type=int, default=1, help="1 = one-shot baseline; 2 = same retries as our arm")
    a = ap.parse_args()
    done = {json.loads(l)["id"] for l in open(a.out)} if os.path.exists(a.out) else set()
    with open(a.out, "a") as out:
        for line in open(a.code):
            r = json.loads(line)
            if r["id"] in done:
                continue
            g = [t for t in r["timeline"] if t["kind"] == "graph"]
            if not g:  # harness failure in the AI-off run: nothing a developer would have seen either
                continue
            row = one(a.pool, r["id"], g[0]["ticks"], g[0].get("alive"), g[0].get("structure"), a.attempts)
            print(json.dumps({k: row.get(k) for k in ("id", "detected", "solved")}), flush=True)
            out.write(json.dumps(row, ensure_ascii=False) + "\n"); out.flush()


if __name__ == "__main__":
    main()
