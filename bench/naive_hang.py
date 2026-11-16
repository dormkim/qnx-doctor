"""Naive baseline for the hang doctor: the same model reads only what a developer has without qnx-doctor —
the program's source and its logs (TICK counts per role) — and guesses the cause and a fix in one reply.
No pidin snapshot, no wait graph, no docs search, no probes. Its fix (edit_file) goes through the same check
as ours: apply to a fresh copy → qcc → boot → rerun; «fixed» only if the rerun shows no cycle/chain and the
stopped loop ticks again. The answer key (labels.json) is never read here; bench/score_hang.py does that.

  python3 bench/naive_hang.py --pool DIR --code runs/x_code.jsonl --out runs/x_naive.jsonl
`--code` = the AI-off run of the same scenarios; only its TICK counts are used (the logs a developer would see).
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qnx_doctor import hang  # noqa: E402
from qnx_doctor.hangdoctor import restarted  # noqa: E402

KINDS = ("deadlock", "priority_chain", "none")
NAIVE_SYSTEM = """You are an experienced QNX 8.0 developer. A message-passing program was started on the target with
run.sh. You have its source files and its logs: for each role log, how many TICK lines it printed in the observation
window (a working loop prints TICK lines; 0 = that loop printed nothing). You have no other tools or observations.
Decide what is wrong. Reply with exactly ONE JSON object, nothing else:
  {"kind": "deadlock" | "priority_chain" | "none", "roles": ["role names involved"], "cause": "short cause",
   "actions": [{"type": "edit_file", "path": "relative path", "find": "exact text", "replace": "new text"}]}
kind: deadlock = processes wait on each other in a cycle of synchronous messages; priority_chain = a high-priority
client waits on a low-priority server that cannot get the CPU (priority inversion); none = nothing is hung (long
waits can be normal). For none give no actions. Only edit_file actions, paths relative to the working directory,
`find` copied exactly from the file. Keep the program's intent; a timeout or sleep that only hides the wait is not a fix."""


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


def one(pool: str, sid: str, ticks: dict) -> dict:
    scen = os.path.join(pool, sid)
    work = hang.prepare(scen)
    try:
        ctx = "\n\n".join([f"Program: {sid} (working directory {work})",
                           "TICK counts per role log in the observation window: " + json.dumps(ticks),
                           "Sources:\n" + hang.sources(work, sid)])
        g = ask(ctx)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    row = {"id": sid, "mode": "naive", "detected": g.get("kind"), "roles": g.get("roles"), "cause": g.get("cause"),
           "actions": g.get("actions") or [], "error": g.get("error"), "solved": None}
    if g.get("kind") in ("deadlock", "priority_chain") and row["actions"]:
        fixed, err = hang.apply_fix(scen, row["actions"])
        if err:
            row.update(solved=False, result=err)
        else:
            res = hang.observe(fixed, sid)
            ok = restarted({"ticks": ticks}, res)
            row.update(solved=ok, result="rerun: no cycle/chain, loop ticks again" if ok else
                       f"still hung: {res.get('graph') or res.get('stage') + ' failed'}")
        shutil.rmtree(fixed, ignore_errors=True)
    elif g.get("kind") in ("deadlock", "priority_chain"):
        row.update(solved=False, result="no fix proposed")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True); ap.add_argument("--code", required=True); ap.add_argument("--out", required=True)
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
            row = one(a.pool, r["id"], g[0]["ticks"])
            print(json.dumps({k: row.get(k) for k in ("id", "detected", "solved")}), flush=True)
            out.write(json.dumps(row, ensure_ascii=False) + "\n"); out.flush()


if __name__ == "__main__":
    main()
