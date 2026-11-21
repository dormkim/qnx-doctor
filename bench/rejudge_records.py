"""Apply the current liveness rule (hangdoctor.not_restarted) to RECORDED reruns — no boot, no AI call.

For the dev sets v3-v5 (sealed, scored once on 2026-11-17/18, opened since): every recorded fix attempt of every arm
is judged again from the states its record holds — first TICK counts and their progress, the rerun's TICK counts,
process count and graph verdict, and the structure reasons recorded at the time. All arms get the same rule. Prints
one table: set x arm x fixed before/after. This is a dev-set recalculation, never a claim: the recorded score tables
are not replaced (bench/DEVSET_RECALC_1121.md), and a claim is measured once on a new sealed set.

What a record cannot show (so the «after» column is an upper bound for the new rule):
  - the rerun's second TICK count (kept only since 2026-11-21): the «still ticking at the second count» part of the
    rule is not applied, only «at least 2 more TICKs than before»;
  - the baseline arms' process count after the rerun (not recorded before 2026-11-21): taken as unchanged; a process
    that went away is still caught by the recorded structure reason («process gone ...»).
v3 records have no progress, so the rule reads them as before (stopped = printed no TICK): no change is possible.

  python3 bench/rejudge_records.py                       # v3, v4, v5 tables
  python3 bench/rejudge_records.py --fake LOG [LOG ...]  # recorded fake_fix_check.py output: every fake still rejected?
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bench"))
from qnx_doctor import hangdoctor as hd  # noqa: E402
import score_structure as ss  # noqa: E402

SETS = {"v3": "results/sealed3_20261117", "v4": "bench/sealed_v4_1117/scored_1118", "v5": "bench/sealed_v5_1118/scored_1118"}
ARMS = ("ai", "naive", "naive_x2")
NO_GRAPH = "no wait cycle and no priority chain"


def _graph(r):
    g = [t for t in r.get("timeline", []) if t.get("kind") == "graph"]
    return g[0] if g else {}


def _attempts(r):
    if "timeline" in r:
        return [t for t in r["timeline"] if t.get("kind") == "ai_fix"]
    return r.get("attempts") or []


def _rerun_clear(e) -> bool:
    """Did the recorded rerun show no cycle/chain? Ours keeps the graph text; a baseline row only its result text."""
    if "rerun_graph" in e:
        return e["rerun_graph"] == NO_GRAPH
    res = str(e.get("result", ""))
    return e.get("live") is True or res.startswith("rerun:") or res == f"still hung: {NO_GRAPH}"


def judge_again(first, e):
    """(live, fixed, why) of one recorded attempt under the current rule; an attempt without a finished rerun (static
    reject, edit not applied, build failed) stays as recorded."""
    if e.get("rerun_tick_counts") is None or e.get("static_reject"):
        return e.get("live"), False, "no finished rerun in the record"
    res = {"ok": True, "judge": {"kind": "none" if _rerun_clear(e) else "hang"}, "graph": e.get("rerun_graph"),
           "ticks": e["rerun_tick_counts"], "alive": e.get("rerun_alive", first.get("alive", 0)), "progress": e.get("rerun_progress")}
    why = hd.not_restarted(first, res)
    return why is None, why is None and not e.get("structure_why"), why


def rejudged(r, code_graph):
    """A copy of one record with every attempt judged again; attempts after the first «fixed» are dropped (the arm
    would have stopped there). Also the list of attempts whose verdict changed."""
    g = _graph(r) or code_graph
    first = {"ticks": g.get("ticks") or r.get("first_ticks") or {}, "progress": g.get("progress"), "alive": g.get("alive") or 0}
    kept, changes = [], []
    for i, e in enumerate(_attempts(r)):
        live, fixed, why = judge_again(first, e)
        was = e.get("solved") is True or str(e.get("result", "")).startswith("SOLVED")
        n = dict(e, live=live, solved=fixed, result="SOLVED (re-judged from the record)" if fixed else (why or "not fixed"))
        kept.append(n)
        if fixed != was or (live is True) != (e.get("live") is True):
            changes.append({"id": r["id"], "try": i + 1, "live": f"{e.get('live')} -> {live}", "fixed": f"{was} -> {fixed}",
                            "structure_why": e.get("structure_why") or [], "first_ticks": first["ticks"], "rerun_ticks": e.get("rerun_tick_counts")})
        if fixed:
            break
    out = dict(r, solved=(any(k["solved"] for k in kept) if kept else r.get("solved")))
    if "timeline" in r:
        out["timeline"] = [t for t in r["timeline"] if t.get("kind") != "ai_fix"] + kept
    else:
        out["attempts"] = kept
    return out, changes


def one_set(name, d):
    labels = {k: v for k, v in json.load(open(os.path.join(ROOT, d, "labels.json"))).items() if not k.startswith("_")}
    ex = os.path.join(ROOT, d, "excluded.json")
    if os.path.exists(ex):
        labels = {k: v for k, v in labels.items() if k not in json.load(open(ex))}
    load = lambda arm: [json.loads(l) for l in open(os.path.join(ROOT, d, f"{arm}.jsonl"))]  # noqa: E731
    code = {r["id"]: _graph(r) for r in load("code")}
    faults = [k for k, v in labels.items() if ss.kind_of(v) not in ss.NO_FAULT]
    old_den = sum(v["kind"] not in ("none", "unknown") for v in labels.values())  # the denominator printed at the time
    rows, changed = [], []
    for arm in ARMS:
        recs = load(arm)
        new = [rejudged(r, code.get(r["id"], {})) for r in recs]
        before, after = ss.score(labels, ss.rows_from(recs)), ss.score(labels, ss.rows_from(n for n, _ in new))
        rows.append((name, arm, old_den, len(faults), before, after))
        changed += [dict(c, set=name, arm=arm, label=ss.kind_of(labels[c["id"]]) if c["id"] in labels else "excluded") for _, cs in new for c in cs]
    return rows, changed


def fake(paths):
    """Recorded fake_fix_check.py runs: a «first» row per scenario, then one row per hand-written fix."""
    bad = lost = n = 0
    print("| scenario | fix | expected | recorded | current rule | structure reasons | ok |\n|---|---|---|---|---|---|---|")
    for p in paths:
        first = {}
        for line in open(p):
            if not line.startswith("{"):
                continue
            r = json.loads(line)
            if "first" in r:
                first[r["id"]] = {"ticks": r.get("ticks") or {}, "progress": r.get("progress"), "alive": r.get("alive") or 0}
                continue
            if "expected_fixed" not in r or r["id"] not in first:
                continue
            rr = r.get("rerun") or {}
            if rr.get("ok"):
                live = hd.not_restarted(first[r["id"]], {"ok": True, "judge": {"kind": rr.get("kind")}, "ticks": rr.get("ticks") or {},
                                                         "alive": rr.get("alive") or 0, "progress": rr.get("progress")}) is None
            else:
                live = False
            now = live and not r.get("structure")
            n += 1
            bad += now and not r["expected_fixed"]  # a fake that passes: the rule must not be adopted
            lost += r["expected_fixed"] and not now
            print(f"| {r['id']} | {r['fix']} | {'fixed' if r['expected_fixed'] else 'rejected'} | {'fixed' if r.get('fixed') else 'rejected'} | "
                  f"{'fixed' if now else 'rejected'} | {len(r.get('structure') or [])} | {'yes' if now == r['expected_fixed'] else 'NO'} |")
    print(f"\n{n} recorded fixes: {bad} fake fixes accepted (must be 0), {lost} real fixes rejected")
    return bad


def main(argv):
    if argv[:1] == ["--fake"]:
        sys.exit(1 if fake(argv[1:]) else 0)
    rows, changed = [], []
    for name, d in SETS.items():
        r, c = one_set(name, d)
        rows += r; changed += c
    print("| set | arm | fixed, as recorded | fixed, current rule | first try fixed, before -> after | false fix (healthy label) | fixed on unknown label | shortcut rejected |")
    print("|---|---|---|---|---|---|---|---|")
    for name, arm, old_den, den, b, a in rows:
        print(f"| {name} | {arm} | {b['fixed']}/{old_den} (of labels with something to fix: {b['fixed']}/{den}) | {a['fixed']}/{den} | "
              f"{b['first']} -> {a['first']} | {b['ff']} -> {a['ff']} | {b['fu']} -> {a['fu']} | {b['short']} -> {a['short']} |")
    print("\n### Attempts whose verdict changed\n| set | arm | id | label | try | alive | fixed | structure reasons recorded | TICKs first -> rerun |\n|---|---|---|---|---|---|---|---|---|")
    for c in changed:
        print(f"| {c['set']} | {c['arm']} | {c['id']} | {c['label']} | {c['try']} | {c['live']} | {c['fixed']} | "
              f"{'; '.join(c['structure_why']) or '-'} | {json.dumps(c['first_ticks'])} -> {json.dumps(c['rerun_ticks'])} |")


if __name__ == "__main__":
    main(sys.argv[1:])
