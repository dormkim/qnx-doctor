"""The hang loop: observe → code judgment → (AI prescription as edit_file) → rebuild + rerun → verdict.

Timeline kinds (report.py): symptom, graph, probe, docs, ai_fix, give_up. No time or latency numbers are kept
(QNX licence 4.2(i)): only states — blocked/running, TICK or not."""
import shutil

from . import hang
from . import structure as st

AI_OFF_NOTE = "code judgment only: the hang is named, no fix is attempted"


MIN_TICKS = 2  # a loop, not one print on the way out


def restarted(first, res):
    """Fixed = the rerun has no cycle/chain AND at least one loop that printed no TICK before now ticks (at least
    MIN_TICKS) AND no loop that was ticking before has stopped AND no process of the program has gone away.
    A «fix» that prints one TICK and exits, breaks a working loop, or makes a peer quit does not count.
    Not «every 0-TICK log must resume»: some roles write a log but never print TICK (sealed D03 server/logger) —
    that stricter rule (set 2026-11-16 before the held-out run) rejected real fixes; replaced after that run."""
    if not res.get("ok") or res["judge"]["kind"] != "none":
        return False
    before, after = first["ticks"], res["ticks"]
    if not any(v == 0 and after.get(k, 0) >= MIN_TICKS for k, v in before.items()):
        return False
    if any(v > 0 and after.get(k, 0) == 0 for k, v in before.items()):
        return False
    return res.get("alive", 0) >= first.get("alive", 0)


def verdict(first, res) -> dict:
    """Fixed = alive again (restarted) AND the same message structure (structure.compare). Both parts are kept, so
    a fix that only passes liveness is counted as a rejected shortcut, not silently as a failure."""
    live = restarted(first, res)
    why = st.compare(first.get("structure"), res.get("structure")) if res.get("ok") else []
    return {"fixed": live and not why, "live": live, "structure": why,
            "unread": st.unread(first.get("structure"), res.get("structure")) if res.get("ok") else []}


def _graph_entry(obs):
    return {"kind": "graph", "verdict": obs["judge"]["kind"], "graph": obs["graph"], "ticks": obs["ticks"],
            "alive": obs.get("alive"), "lines": obs["pidin_lines"], "structure": obs.get("structure")}


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
        v = {"fixed": False, "live": None, "structure": []}
        if err:
            msg = err
            res = None
        else:
            res = hang.observe(fixed, name, focus)
            v = verdict(first, res)
            res["healthy"] = v["fixed"]
            msg = ("SOLVED (rerun: no cycle/chain, the stopped loop ticks again, same message structure)" if v["fixed"] else
                   "rejected: alive again but the message structure changed: " + "; ".join(v["structure"]) if v["live"] else
                   f"still hung: {res.get('graph') or res.get('stage') + ' failed: ' + res.get('log', '')}")
        entry = {"kind": "ai_fix", "cause": payload.get("cause"), "culprit": payload.get("culprit"),
                 "evidence": payload.get("evidence"), "doc_refs": payload.get("doc_refs"), "actions": acts,
                 "diff": hang.diff(work, fixed, name), "result": msg, "live": v["live"], "structure_why": v["structure"], "unread": v.get("unread"),
                 "static_reject": bool(err and err.startswith(st.STATIC)), "pids_ok": hang.pids_checked(payload, first),
                 **hang.checked_claims(work, payload)}
        if res and res.get("ok"):
            entry["rerun_graph"] = res["graph"]
            entry["rerun_ticks"] = {k: ("yes" if v else "no") for k, v in res["ticks"].items()}
            entry["rerun_tick_counts"], entry["rerun_alive"] = res["ticks"], res.get("alive")  # states for re-judging
        timeline.append(entry)
        tried.append({"actions": acts, "result": msg})
        shutil.rmtree(fixed, ignore_errors=True)
        if res and res.get("healthy"):
            shutil.rmtree(work, ignore_errors=True)
            return {"id": sid, "solved": True, "by": "ai", "detected": detected, "cause": payload.get("cause"),
                    "cause_label": entry["cause_label"], "culprit_in_source": entry["culprit_in_source"],
                    "culprit": payload.get("culprit"), "actions": acts, "timeline": timeline}
    shutil.rmtree(work, ignore_errors=True)
    return {"id": sid, "solved": False, "by": "ai", "detected": detected, "timeline": timeline}
