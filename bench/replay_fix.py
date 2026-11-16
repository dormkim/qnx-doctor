"""Re-judge recorded fixes after a verifier change — same edits, no new AI call.

For each row whose recorded attempt ended «still hung: no wait cycle and no priority chain» (the cycle was gone
but the TICK/alive rule said no), re-apply exactly the recorded edit_file actions to a fresh copy, rerun on the
target, and apply the current hangdoctor.restarted. Reported separately from the as-run numbers (post-hoc).

  python3 bench/replay_fix.py --pool DIR --code runs/x_code.jsonl --run runs/x_ai.jsonl --out runs/x_ai_replay.jsonl
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qnx_doctor import hang  # noqa: E402
from qnx_doctor.hangdoctor import restarted  # noqa: E402

GONE = "still hung: no wait cycle and no priority chain"


def attempts(row):
    if row.get("mode") == "naive":
        return [row["actions"]] if str(row.get("result", "")).startswith(GONE) else []
    return [t["actions"] for t in row.get("timeline", []) if t.get("kind") == "ai_fix" and str(t.get("result", "")).startswith(GONE)]


def main():
    ap = argparse.ArgumentParser()
    for f in ("--pool", "--code", "--run", "--out"):
        ap.add_argument(f, required=True)
    a = ap.parse_args()
    first = {}
    for l in open(a.code):
        r = json.loads(l)
        g = [t for t in r["timeline"] if t["kind"] == "graph"]
        if g:
            first[r["id"]] = {"ticks": g[0]["ticks"], "alive": g[0].get("alive") or 0}
    with open(a.out, "w") as out:
        for l in open(a.run):
            r = json.loads(l)
            if r.get("solved") is True or r["id"] not in first:
                continue
            for acts in attempts(r):
                fixed, err = hang.apply_fix(os.path.join(a.pool, r["id"]), acts)
                res = {"ok": False} if err else hang.observe(fixed, r["id"])
                shutil.rmtree(fixed, ignore_errors=True)
                ok = restarted(first[r["id"]], res)
                row = {"id": r["id"], "mode": r.get("mode"), "replayed": True, "solved": ok, "error": err,
                       "rerun_ticks": res.get("ticks"), "rerun_alive": res.get("alive"), "rerun_kind": (res.get("judge") or {}).get("kind")}
                out.write(json.dumps(row) + "\n"); out.flush()
                print(json.dumps({k: row[k] for k in ("id", "mode", "solved")}), flush=True)
                if ok:
                    break


if __name__ == "__main__":
    main()
