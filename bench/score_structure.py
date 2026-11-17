"""Score hang runs with the «same message structure» verifier. Reads labels.json (the only scorer that does, with
score_hang.py). One table row per arm:

  kind found         the kind the arm named = label kind (code/AI arm: the code's judgment; naive: its own guess)
  false alarm        label none, arm named a hang
  fixed (structure)  proven by rerun: alive again AND the same processes and message pairs (hangdoctor.verdict),
                     with every try the arm had (ours: up to 2; naive: 1; naive_x2: 2)
  first try fixed    the same, counting only the arm's first try. Shown next to «fixed» so a gain from the retry
                     loop is not read as a gain from the pidin graph (red team 2026-11-16)
  shortcut rejected  fix attempts that came back alive (or edited run.sh / the harness) but changed the structure
  liveness-only      fixes a liveness-only verifier would have accepted (the 2026-11-16 first-run rule)
  false fix          «fixed» on a label-none scenario (must be 0)
  fixed on unknown   «fixed» on a label-unknown scenario: its own column, neither «fixed» nor «false fix»

Sealed v3 rules (bench/sealed_v3_1117/README.md, added before its single run, 2026-11-17):
  unknown        label for a stop outside the closed vocabulary. Hit = the arm names none of the three hang kinds AND
                 does not call the system healthy. Up to v3 the code/our arm said this as detected «none» with the note
                 «loop not running but no wait cycle or chain found» -> read as «unknown». Since 2026-11-17 (before
                 sealed v4) hangdoctor says detected «unknown» itself (note «unknown (spinning|blocked_other|no_info):
                 ...»); both forms read as «unknown», so v3 outputs score exactly as before. A naive arm only has the
                 four words; its literal output is listed and it scores 0 unless it says «unknown».
  accept_kinds   multi-cause label: the kind counts as found if the arm names any of them.
  loop_logs      «fixed» also needs every loop in loop_logs that printed no TICK first to tick again (>= 2) in the
                 rerun of the try that fixed it. A loop_logs role not found in the TICK counts is reported, not skipped.
  --exclude-file JSON {id: reason} of scenarios whose unmodified run did not match its «expect»: listed with the
                 reason, not scored (their labels are not edited).

  python3 bench/score_structure.py LABELS.json --fresh code=runs/x_code.jsonl ai=runs/x_ai.jsonl naive=runs/x_naive.jsonl
  python3 bench/score_structure.py LABELS.json --rejudge runs/x_rejudge.jsonl
States only, no timing (QNX licence 4.6(i)).
"""
import json
import sys

KINDS = ("deadlock", "priority_chain", "missing_reply", "none", "unknown")
HANGS = ("deadlock", "priority_chain", "missing_reply")
NOT_RUNNING_NOTE = "loop not running"  # hangdoctor.diagnose_hang: stopped, but no cycle or chain in the graph
MIN_TICKS = 2  # the same «a loop, not one print» bar as hangdoctor.MIN_TICKS


def _shortcut(e):
    return bool(e.get("static_reject")) or (e.get("live") is True and bool(e.get("structure_why")))


def _first_ok(e):
    return e.get("solved") is True or str(e.get("result", "")).startswith("SOLVED")


def _detected(r):
    """The kind an arm named. «unknown» either way: the explicit word (hangdoctor since 2026-11-17) or the v3-era
    «none» + NOT_RUNNING_NOTE. A healthy «none» («no hang found») stays «none»."""
    d = r.get("detected")
    if d == "unknown" or (d == "none" and str(r.get("note", "")).startswith(NOT_RUNNING_NOTE)):
        return "unknown"
    return d


def _rerun_ticks(e):
    return e.get("rerun_tick_counts")


def _first_ticks(r):
    g = [t for t in r.get("timeline", []) if t.get("kind") == "graph"]
    return g[0].get("ticks") if g else r.get("first_ticks")


def fresh_rows(arm, path):
    out = {}
    for line in open(path):
        r = json.loads(line)
        if "timeline" not in r:  # naive arms (one-shot «naive» or «naive_x2»): tries listed in r["attempts"]
            att = r.get("attempts")
            if att is None:  # rows written before 2026-11-16 evening: one try, its fields at top level
                att = [r] if r.get("actions") and r.get("detected") in ("deadlock", "priority_chain", "missing_reply") else []
        else:
            att = [t for t in r.get("timeline", []) if t.get("kind") == "ai_fix"]
        solving = [e for e in att if _first_ok(e)]
        out[r["id"]] = {"detected": _detected(r), "raw": r.get("detected"), "note": r.get("note") or r.get("error") or r.get("cause"),
                        "first_ticks": _first_ticks(r), "fix_ticks": _rerun_ticks(solving[-1]) if solving else None,
                        "first_ticks_try": _rerun_ticks(att[0]) if att else None,
                        "fixed": r.get("solved") is True,
                        "first": bool(att) and _first_ok(att[0]) and r.get("solved") is True,
                        "tries": len(att),
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
            "live_only": r.get("as_run_fixed") is True, "harness": r.get("harness", False), "first": None}
    return arms


def hit(lab, detected):
    """Kind found: the label kind, any of accept_kinds, or for «unknown» an explicit «not one of the hang kinds»."""
    if lab["kind"] == "unknown":
        return detected not in HANGS + ("none", None)
    return detected == lab["kind"] or detected in lab.get("accept_kinds", [])


def _norm(role):
    return str(role).rsplit("/", 1)[-1].removesuffix(".log")


def _tick(ticks, role):
    """TICK count of a loop_logs role (written as «d0x», «/tmp/d0x.log» or «x»); None if the role is not there."""
    ticks = ticks or {}
    for k in (_norm(role), "d0" + _norm(role)):
        if k in ticks:
            return ticks[k]
    return None


def loops_ok(lab, first, after):
    """Every loop_logs role that printed no TICK first ticks again (>= MIN_TICKS) after the fix. No loop_logs = True."""
    stopped = [x for x in lab.get("loop_logs", []) if not _tick(first, x)]
    return all((_tick(after, x) or 0) >= MIN_TICKS for x in stopped)


def missing_roles(lab, r):
    return [x for x in lab.get("loop_logs", []) if r and r.get("first_ticks") is not None and _tick(r["first_ticks"], x) is None]


def _fixed(lab, r):
    """The verifier's «fixed» plus the loop_logs rule. Rows recorded before rerun TICK counts were kept (re-judged
    or older runs) have no fix_ticks: they keep the verifier's verdict."""
    if not r["fixed"]:
        return False
    if not lab.get("loop_logs") or r.get("fix_ticks") is None:
        return True
    return loops_ok(lab, r.get("first_ticks"), r.get("fix_ticks"))


def _first(lab, r):
    if r.get("first") is None:
        return None
    if not r["first"] or not lab.get("loop_logs") or r.get("first_ticks_try") is None:
        return bool(r["first"])
    return loops_ok(lab, r.get("first_ticks"), r.get("first_ticks_try"))


def score(labels, rows):
    s = {"hit": {k: 0 for k in KINDS}, "n": {k: 0 for k in KINDS}, "fa": 0, "fixed": 0, "first": 0, "short": 0, "live": 0, "ff": 0,
         "fu": 0, "harness": 0, "loop_cut": 0}
    for sid, lab in labels.items():
        k = lab["kind"]
        s["n"][k] += 1
        r = rows.get(sid)
        if r is None or r["harness"]:
            s["harness"] += 1
            continue
        fault = k not in ("none", "unknown")
        fx = _fixed(lab, r)
        s["hit"][k] += hit(lab, r["detected"])
        s["fa"] += k == "none" and r["detected"] not in ("none", None)
        s["fixed"] += fx and fault
        s["loop_cut"] += r["fixed"] and not fx and fault
        s["first"] += bool(_first(lab, r)) and fault
        s["ff"] += r["fixed"] and k == "none"
        s["fu"] += r["fixed"] and k == "unknown"
        s["short"] += r["shortcuts"]
        s["live"] += r["live_only"] and fault
    return s


def table(labels, arms):
    faults = sum(v["kind"] not in ("none", "unknown") for v in labels.values())
    out = ["| arm | kind found | deadlock | priority chain | missing reply | healthy | unknown | false alarm | first try fixed | fixed incl. retries (same structure) | shortcut rejected | liveness-only would accept | false fix | fixed on unknown |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, rows in arms.items():
        s = score(labels, rows)
        tot = sum(s["hit"].values())
        fix = "-" if arm == "code" else f"{s['fixed']}/{faults}"
        first = "-" if arm == "code" or any(r.get("first") is None for r in rows.values()) else f"{s['first']}/{faults}"
        short = "-" if arm == "code" else str(s["short"])
        live = "-" if arm == "code" else f"{s['live']}/{faults}"
        out.append(f"| {arm} | {tot}/{len(labels)} | " + " | ".join(f"{s['hit'][k]}/{s['n'][k]}" for k in KINDS) +
                   f" | {s['fa']}/{s['n']['none']} | {first} | {fix} | {short} | {live} | {s['ff']} | {'-' if arm == 'code' else s['fu']} |"
                   + (f" harness {s['harness']}" if s["harness"] else "") + (f" loop_logs cut {s['loop_cut']}" if s["loop_cut"] else ""))
    return "\n".join(out)


def details(labels, arms):
    """Literal outputs on «unknown» labels, fixes on info_insufficient labels (for a human), loop_logs problems."""
    out = []
    unk = [i for i, v in labels.items() if v["kind"] == "unknown"]
    if unk:
        out += ["### Literal outputs on «unknown» labels", "| id | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
        for i in unk:
            out.append(f"| {i} | " + " | ".join(
                f"{(arms[a].get(i) or {}).get('raw')} ({str((arms[a].get(i) or {}).get('note') or '')[:80]})" for a in arms) + " |")
    ins = [(a, i) for i, v in labels.items() if v.get("info_insufficient") for a in arms if (arms[a].get(i) or {}).get("fixed")]
    if ins:
        out += ["", "### «Fixed» on info_insufficient labels (read by a human)"] + [f"- {a} {i}" for a, i in ins]
    miss = [(i, x) for i, v in labels.items() for x in missing_roles(v, next((arms[a].get(i) for a in arms if arms[a].get(i)), None))]
    if miss:
        out += ["", "### loop_logs roles not found in the TICK counts"] + [f"- {i}: {x}" for i, x in miss]
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
        cells = [f"{sum(hit(labels[i], arms[a].get(i, {}).get('detected')) for i in ids)}/{len(ids)}" for a in arms]
        fl = [i for i in ids if labels[i]["kind"] not in ("none", "unknown")]
        fx = [f"{sum(bool(arms[a].get(i)) and _fixed(labels[i], arms[a][i]) for i in fl)}/{len(fl)}" for a in arms if a != "code"]
        out.append(f"| {ax} | {len(ids)} | " + " | ".join(cells) + " | " + " | ".join(fx) + " |")
    return "\n".join(out)


def main(argv):
    labels = {k: v for k, v in json.load(open(argv[0])).items() if not k.startswith("_")}
    excluded = {}
    if "--exclude-file" in argv:
        j = argv.index("--exclude-file")
        excluded = json.load(open(argv[j + 1]))
        argv = argv[:j] + argv[j + 2:]
        labels = {k: v for k, v in labels.items() if k not in excluded}
    if excluded:
        print(f"Excluded (unmodified run did not match «expect»): {len(excluded)}")
        print("\n".join(f"- {k}: {v}" for k, v in sorted(excluded.items())) + "\n")
    if argv[1] == "--rejudge":
        arms = rejudge_rows(argv[2])
    else:
        arms = {kv.split("=", 1)[0]: fresh_rows(kv.split("=", 1)[0], kv.split("=", 1)[1]) for kv in argv[2:]}
    print(table(labels, arms))
    ax = by_axis(labels, arms)
    if ax:
        print("\n" + ax)
    d = details(labels, arms)
    if d:
        print("\n" + d)


if __name__ == "__main__":
    main(sys.argv[1:])
