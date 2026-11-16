"""Re-judge recorded hang fixes with the «same message structure» verifier — same edits, no new AI call.

For each scenario: boot the original once with the current harness (pidin + message records), then apply each
arm's recorded fix to a fresh copy, rerun, and judge with hangdoctor.verdict (alive again AND same structure).
  AI arm     the fix that was accepted as run (the solved attempt); unsolved rows have nothing to re-judge
  naive arm  its single fix, whatever the as-run result was
Rows: {id, arm, fixed, live, structure_why, static_reject, detected}. Plus one «code» row per scenario (the kind
the code names on this boot). States only (QNX licence 4.6(i)).

  python3 bench/rejudge_hang.py --pool DIR --ai runs/x_ai.jsonl --naive runs/x_naive.jsonl --out runs/x_rejudge.jsonl
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


def recorded(path, arm):
    out = {}
    for line in open(path):
        r = json.loads(line)
        if arm == "naive":
            out[r["id"]] = {"actions": r.get("actions") or [], "detected": r.get("detected"), "as_run": r.get("solved")}
        else:
            out[r["id"]] = {"actions": r.get("actions") if r.get("solved") else [], "detected": r.get("detected"), "as_run": r.get("solved")}
    return out


def judge(scen, sid, first, acts):
    fixed, err = hang.apply_fix(scen, acts)
    if err:
        shutil.rmtree(fixed, ignore_errors=True)
        return {"fixed": False, "live": None, "structure_why": [err], "static_reject": err.startswith(st.STATIC)}
    res = hang.observe(fixed, sid)
    shutil.rmtree(fixed, ignore_errors=True)
    v = verdict(first, res)
    return {"fixed": v["fixed"], "live": v["live"], "structure_why": v["structure"], "static_reject": False, "unread": v["unread"], "after_structure": res.get("structure"),
            "rerun_kind": (res.get("judge") or {}).get("kind"), "rerun_ticks": res.get("ticks")}


def main():
    ap = argparse.ArgumentParser()
    for f in ("--pool", "--ai", "--naive", "--out"):
        ap.add_argument(f, required=True)
    a = ap.parse_args()
    arms = {"ai": recorded(a.ai, "ai"), "naive": recorded(a.naive, "naive")}
    done = {(json.loads(l)["id"], json.loads(l)["arm"]) for l in open(a.out)} if os.path.exists(a.out) else set()
    with open(a.out, "a") as out:
        for sid in sorted(set(arms["ai"]) | set(arms["naive"])):
            if all((sid, k) in done for k in ("code", "ai", "naive")):
                continue
            scen = os.path.join(a.pool, sid)
            work = hang.prepare(scen)
            first = hang.observe(work, sid)
            shutil.rmtree(work, ignore_errors=True)
            rows = [{"id": sid, "arm": "code", "detected": (first.get("judge") or {}).get("kind") if first.get("ok") else None,
                     "harness": not first.get("ok"), "structure": first.get("structure")}]
            for arm, rec in arms.items():
                r = rec.get(sid)
                if r is None:
                    continue
                row = {"id": sid, "arm": arm, "detected": r["detected"], "as_run_fixed": r["as_run"], "n_actions": len(r["actions"])}
                if r["actions"] and first.get("ok") and r["detected"] in ("deadlock", "priority_chain", "missing_reply"):
                    row.update(judge(scen, sid, first, r["actions"]))
                rows.append(row)
            for row in rows:
                out.write(json.dumps(row) + "\n"); out.flush()
                print(json.dumps({k: row.get(k) for k in ("id", "arm", "detected", "as_run_fixed", "fixed", "live")}), flush=True)


if __name__ == "__main__":
    main()
