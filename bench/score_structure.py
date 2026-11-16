"""Score hang runs with the «same message structure» verifier. Reads labels.json (the only scorer that does, with
score_hang.py). One table row per arm:

  kind found         the kind the arm named = label kind (code/AI arm: the code's judgment; naive: its own guess)
  false alarm        label none, arm named a hang
  fixed (structure)  proven by rerun: alive again AND the same processes and message pairs (hangdoctor.verdict)
  shortcut rejected  fix attempts that came back alive (or edited run.sh / the harness) but changed the structure
  liveness-only      fixes a liveness-only verifier would have accepted (the 2026-11-16 first-run rule)
  false fix          «fixed» on a label-none scenario (must be 0)

  python3 bench/score_structure.py LABELS.json --fresh code=runs/x_code.jsonl ai=runs/x_ai.jsonl naive=runs/x_naive.jsonl
  python3 bench/score_structure.py LABELS.json --rejudge runs/x_rejudge.jsonl
States only, no timing (QNX licence 4.2(i)).
"""
import json
import sys

KINDS = ("deadlock", "priority_chain", "none")


def _shortcut(e):
    return bool(e.get("static_reject")) or (e.get("live") is True and bool(e.get("structure_why")))


def fresh_rows(arm, path):
    out = {}
    for line in open(path):
        r = json.loads(line)
        if arm == "naive":
            att = [r] if r.get("actions") and r.get("detected") in ("deadlock", "priority_chain") else []
        else:
            att = [t for t in r.get("timeline", []) if t.get("kind") == "ai_fix"]
        out[r["id"]] = {"detected": r.get("detected"), "fixed": r.get("solved") is True,
                        "shortcuts": sum(_shortcut(e) for e in att),
                        "live_only": any(e.get("live") is True or (e.get("live") is None and str(e.get("result", "")).startswith("SOLVED")) for e in att)
                        or (r.get("solved") is True),
                        "harness": r.get("by") == "harness"}
    return out


def rejudge_rows(path):
    arms = {}
    for line in open(path):
        r = json.loads(line)
        arms.setdefault(r["arm"], {})[r["id"]] = {
            "detected": r.get("detected"), "fixed": r.get("fixed") is True, "shortcuts": int(_shortcut(r)),
            "live_only": r.get("as_run_fixed") is True, "harness": r.get("harness", False)}
    return arms


def score(labels, rows):
    s = {"hit": {k: 0 for k in KINDS}, "n": {k: 0 for k in KINDS}, "fa": 0, "fixed": 0, "short": 0, "live": 0, "ff": 0, "harness": 0}
    for sid, lab in labels.items():
        k = lab["kind"]
        s["n"][k] += 1
        r = rows.get(sid)
        if r is None or r["harness"]:
            s["harness"] += 1
            continue
        s["hit"][k] += r["detected"] == k
        s["fa"] += k == "none" and r["detected"] not in ("none", None)
        s["fixed"] += r["fixed"] and k != "none"
        s["ff"] += r["fixed"] and k == "none"
        s["short"] += r["shortcuts"]
        s["live"] += r["live_only"] and k != "none"
    return s


def table(labels, arms):
    faults = sum(v["kind"] != "none" for v in labels.values())
    out = ["| arm | kind found | deadlock | priority chain | healthy | false alarm | fixed (same structure) | shortcut rejected | liveness-only would accept | false fix |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for arm, rows in arms.items():
        s = score(labels, rows)
        tot = sum(s["hit"].values())
        fix = "-" if arm == "code" else f"{s['fixed']}/{faults}"
        short = "-" if arm == "code" else str(s["short"])
        live = "-" if arm == "code" else f"{s['live']}/{faults}"
        out.append(f"| {arm} | {tot}/{len(labels)} | " + " | ".join(f"{s['hit'][k]}/{s['n'][k]}" for k in KINDS) +
                   f" | {s['fa']}/{s['n']['none']} | {fix} | {short} | {live} | {s['ff']} |" + (f" harness {s['harness']}" if s["harness"] else ""))
    return "\n".join(out)


def by_axis(labels, arms):
    """Kind found per v2 axis (a scenario counts under every axis it has)."""
    axes = sorted({a for v in labels.values() for a in v.get("axes", [])})
    if not axes:
        return ""
    out = ["| axis | n | " + " | ".join(f"{arm} kind found" for arm in arms) + " | " + " | ".join(f"{arm} fixed" for arm in arms if arm != "code") + " |",
           "|---|---|" + "---|" * (2 * len(arms) - 1)]
    for ax in axes:
        ids = [k for k, v in labels.items() if ax in v.get("axes", [])]
        cells = [f"{sum(arms[a].get(i, {}).get('detected') == labels[i]['kind'] for i in ids)}/{len(ids)}" for a in arms]
        nf = sum(labels[i]["kind"] != "none" for i in ids)
        fx = [f"{sum(bool(arms[a].get(i, {}).get('fixed')) for i in ids)}/{nf}" for a in arms if a != "code"]
        out.append(f"| {ax} | {len(ids)} | " + " | ".join(cells) + " | " + " | ".join(fx) + " |")
    return "\n".join(out)


def main(argv):
    labels = {k: v for k, v in json.load(open(argv[0])).items() if not k.startswith("_")}
    if argv[1] == "--rejudge":
        arms = rejudge_rows(argv[2])
    else:
        arms = {kv.split("=", 1)[0]: fresh_rows(kv.split("=", 1)[0], kv.split("=", 1)[1]) for kv in argv[2:]}
    print(table(labels, arms))
    ax = by_axis(labels, arms)
    if ax:
        print("\n" + ax)


if __name__ == "__main__":
    main(sys.argv[1:])
