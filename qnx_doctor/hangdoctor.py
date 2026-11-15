"""The hang loop: observe → code judgment → (AI prescription as edit_file) → rebuild + rerun → verdict.

Timeline kinds (report.py): symptom, graph, probe, docs, ai_fix, give_up. No time or latency numbers are kept
(QNX licence 4.2(i)): only states — blocked/running, TICK or not."""
import shutil

from . import hang

AI_OFF_NOTE = "code judgment only: the hang is named, no fix is attempted"


def restarted(first, res):
    """Fixed = rerun has no cycle/chain AND a loop that printed no TICK before now prints TICKs."""
    if not res.get("ok") or res["judge"]["kind"] != "none":
        return False
    return any(first["ticks"].get(k) == 0 and v > 0 for k, v in res["ticks"].items())


def _graph_entry(obs):
    return {"kind": "graph", "verdict": obs["judge"]["kind"], "graph": obs["graph"], "ticks": obs["ticks"],
            "lines": obs["pidin_lines"]}


def diagnose_hang(scen_dir, use_ai=True, index=None, focus=None, max_fixes=2, sid=None):
    sid = sid or scen_dir.rstrip("/").split("/")[-1]
    name = sid
    timeline, tried = [], []
    work = hang.prepare(scen_dir)
    first = hang.observe(work, name, focus)
    if not first["ok"]:
        timeline.append({"kind": "symptom", "reason": f"{first['stage']} failed", "out": first["log"]})
        shutil.rmtree(work, ignore_errors=True)
        return {"id": sid, "solved": False, "by": "harness", "detected": None, "timeline": timeline}
    timeline.append({"kind": "symptom", "reason": "loop stopped" if not first["healthy"] else "loop running",
                     "out": "TICKs per role: " + ", ".join(f"{k} {'yes' if v else 'no'}" for k, v in first["ticks"].items())})
    timeline.append(_graph_entry(first))
    detected = first["judge"]["kind"]
    if first["healthy"] or detected == "none":
        shutil.rmtree(work, ignore_errors=True)
        return {"id": sid, "solved": None, "by": "code", "detected": detected,
                "note": "no hang found" if first["healthy"] else "loop not running but no wait cycle or chain found",
                "timeline": timeline}
    if not use_ai:
        shutil.rmtree(work, ignore_errors=True)
        return {"id": sid, "solved": False, "by": "code", "detected": detected, "note": AI_OFF_NOTE, "timeline": timeline}
    from . import ai
    for _ in range(max_fixes):
        kind, payload, _m = ai.think(hang.context(work, name, first, tried), work, hang.base_env(), index, timeline,
                                     system=hang.HANG_SYSTEM, confine=True)
        if kind == "give_up":
            timeline.append({"kind": "give_up", "why": payload})
            break
        acts = payload.get("actions", [])
        fixed, err = hang.apply_fix(scen_dir, acts)
        if err:
            msg = err
            res = None
        else:
            res = hang.observe(fixed, name, focus)
            res["healthy"] = restarted(first, res)
            msg = ("SOLVED (rerun: no cycle/chain, the stopped loop ticks again)" if res["healthy"] else
                   f"still hung: {res.get('graph') or res.get('stage') + ' failed: ' + res.get('log', '')}")
        entry = {"kind": "ai_fix", "cause": payload.get("cause"), "culprit": payload.get("culprit"),
                 "evidence": payload.get("evidence"), "doc_refs": payload.get("doc_refs"), "actions": acts,
                 "diff": hang.diff(work, fixed, name), "result": msg}
        if res and res.get("ok"):
            entry["rerun_graph"] = res["graph"]
            entry["rerun_ticks"] = {k: ("yes" if v else "no") for k, v in res["ticks"].items()}
        timeline.append(entry)
        tried.append({"actions": acts, "result": msg})
        shutil.rmtree(fixed, ignore_errors=True)
        if res and res.get("healthy"):
            shutil.rmtree(work, ignore_errors=True)
            return {"id": sid, "solved": True, "by": "ai", "detected": detected, "cause": payload.get("cause"),
                    "culprit": payload.get("culprit"), "actions": acts, "timeline": timeline}
    shutil.rmtree(work, ignore_errors=True)
    return {"id": sid, "solved": False, "by": "ai", "detected": detected, "timeline": timeline}
