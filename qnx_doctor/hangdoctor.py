"""The hang loop: observe → code judgment → (AI prescription as edit_file) → rebuild + rerun → verdict.

Timeline kinds (report.py): symptom, graph, probe, docs, ai_fix, give_up. No time or latency numbers are kept
(QNX licence 4.6(i)): only states — blocked/running, TICK or not."""
import shutil

from . import hang
from . import progress as pg
from . import source_check
from . import structure as st

AI_OFF_NOTE = "code judgment only: the hang is named, no fix is attempted"


MIN_TICKS = 2  # a loop, not one print on the way out


STOPPED = (pg.FLAT, pg.IDLE, pg.GONE)
NOT_ALIVE = "not proven alive"  # every liveness failure that is not «still hung» starts with these words


def stopped_roles(first) -> list[str]:
    """Role logs whose loop was not moving at the hung observation: flat, idle or missing between the two TICK counts
    of that boot (progress.moves). Recordings without a second count (older harness) fall back to «printed no TICK»."""
    mv = first.get("progress")
    if mv:
        return [k for k in first["ticks"] if mv.get(k) in STOPPED]
    return [k for k, v in first["ticks"].items() if v == 0]


def not_restarted(first, res) -> str | None:
    """None = alive again. Otherwise the condition that failed, in words (given back to the AI and the baseline, so
    a retry is aimed at what actually failed).

    Alive again = the rerun has no cycle/chain AND at least one loop that was stopped at the first observation printed
    at least MIN_TICKS more TICKs than it had then AND (when the rerun has a second count) was still ticking between
    the rerun's two counts AND no loop that had ticked prints nothing now AND no program process has gone away.

    Changed 2026-11-21 (dev sets v3-v5, before sealed v6). Until then «stopped» meant «printed no TICK at all». A
    ring whose members each print one TICK before the first send, or a server that stops replying after a few
    rounds, has no 0-TICK role, so no fix of any arm could pass (v4 D03, v5 E05/E06/E08; the recorded reruns showed no
    cycle, the same processes and far more TICKs). «Stopped» is now read from progress. The bar moved with it: more
    TICKs than before, not just MIN_TICKS, and still growing at the second count, so a «fix» that lets a loop print a
    little more and stop again does not count.
    Not «every stopped log must resume»: some roles write a log but never print TICK (sealed D03 server/logger) —
    that stricter rule (set 2026-11-16 before the held-out run) rejected real fixes; replaced after that run."""
    if not res.get("ok"):
        # Never the tool's own words: compiler and guest output can quote files (blocker 4, 2026-11-22).
        where = source_check.locations(res.get("log", "")) if res.get("stage") == "build" else []
        return f"rerun did not finish: {res.get('stage')} failed" + (f" (errors at {', '.join(where)})" if where else "")
    if res["judge"]["kind"] != "none":
        return f"still hung: {res.get('graph') or res['judge']['kind']}"
    before, after = first["ticks"], res["ticks"]
    stopped = stopped_roles(first)
    if not stopped:
        return f"{NOT_ALIVE}: no loop was stopped at the first observation, so there is nothing to show as restarted"
    more = [k for k in stopped if after.get(k, 0) >= before[k] + MIN_TICKS]
    if not more:
        return (f"{NOT_ALIVE}: no cycle or chain in the rerun, but no stopped loop printed at least {MIN_TICKS} more "
                "TICKs than before (TICK counts before -> after: "
                + ", ".join(f"{k} {before[k]} -> {after.get(k, 'no log')}" for k in stopped) + ")")
    mv = res.get("progress")
    if mv is not None and not any(mv.get(k) == pg.GREW for k in more):
        return (f"{NOT_ALIVE}: a stopped loop printed more TICKs but was not ticking any more at the second count of "
                "the rerun (" + ", ".join(f"{k} {mv.get(k)}" for k in more) + ")")
    quiet = [k for k, v in before.items() if v > 0 and after.get(k, 0) == 0]
    if quiet:
        return f"{NOT_ALIVE}: a loop that had printed TICKs prints none in the rerun ({', '.join(quiet)})"
    if res.get("alive", 0) < first.get("alive", 0):
        return f"{NOT_ALIVE}: a program process is gone ({first.get('alive', 0)} -> {res.get('alive', 0)} processes)"
    return None


def restarted(first, res) -> bool:
    return not_restarted(first, res) is None


def verdict(first, res) -> dict:
    """Fixed = alive again (restarted) AND the same message structure (structure.compare). Both parts are kept, so
    a fix that only passes liveness is counted as a rejected shortcut, not silently as a failure."""
    not_live = not_restarted(first, res)
    live = not_live is None
    why = st.compare(first.get("structure"), res.get("structure")) if res.get("ok") else []
    return {"fixed": live and not why, "live": live, "structure": why, "why_not_live": not_live,
            "unread": st.unread(first.get("structure"), res.get("structure")) if res.get("ok") else []}


UNKNOWN_NOTE = "unknown"  # every «unknown» note starts with this word (bench/score_structure.py reads it)


def named(obs) -> tuple[str, str]:
    """(detected, note). detected: a hang kind, «none» (healthy) or «unknown» (2026-11-17, before sealed v4).
    Before, a stop the wait graph could not name came out as detected «none» with the note «loop not running but no
    wait cycle or chain found», and only the scorer read that as «unknown». Now the tool says «unknown» itself and
    why: spinning on the CPU, blocked outside message passing, or not enough information (progress.classify)."""
    live = obs.get("liveness") or pg.classify(obs["judge"]["kind"], [], [], "", obs["ticks"], None)
    d = pg.detected(live["state"], obs["judge"]["kind"])
    if d == "none":
        return d, "no hang found"
    if d == "unknown":
        return d, f"{UNKNOWN_NOTE} ({live['state']}): {live['why']}"
    return d, ""


def result_text(v) -> str:
    """One line for the timeline and for the next try. A failed try names the condition that failed (2026-11-21:
    «still hung: no wait cycle and no priority chain» sent retries the wrong way, v5 E08)."""
    if v["fixed"]:
        return "SOLVED (rerun: no cycle/chain, the stopped loop ticks again, same message structure)"
    if v["live"]:
        return "rejected: alive again but the message structure changed: " + "; ".join(v["structure"])
    return v["why_not_live"]


def _graph_entry(obs):
    return {"kind": "graph", "verdict": obs["judge"]["kind"], "graph": obs["graph"], "ticks": obs["ticks"],
            "progress": obs.get("progress"), "liveness": obs.get("liveness"),
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
    detected, why = named(first)
    if detected in ("none", "unknown"):  # nothing to fix: the AI is not called and no fix is claimed
        shutil.rmtree(work, ignore_errors=True)
        return {"id": sid, "solved": None, "by": "code", "detected": detected, "note": why,
                "liveness": first.get("liveness", {}).get("state"), "timeline": timeline}
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
        v = {"fixed": False, "live": None, "structure": [], "why_not_live": None}
        if err:
            msg = err
            res = None
        else:
            res = hang.observe(fixed, name, focus)
            v = verdict(first, res)
            res["healthy"] = v["fixed"]
            msg = result_text(v)
        entry = {"kind": "ai_fix", "cause": payload.get("cause"), "culprit": payload.get("culprit"),
                 "evidence": payload.get("evidence"), "doc_refs": payload.get("doc_refs"), "actions": acts,
                 "diff": hang.diff(work, fixed, name), "result": msg, "live": v["live"], "structure_why": v["structure"], "unread": v.get("unread"),
                 "static_reject": bool(err and err.startswith(st.STATIC)), "pids_ok": hang.pids_checked(payload, first),
                 **hang.checked_claims(work, payload)}
        if res and res.get("ok"):
            entry["rerun_graph"] = res["graph"]
            entry["rerun_ticks"] = {k: ("yes" if v else "no") for k, v in res["ticks"].items()}
            entry["rerun_tick_counts"], entry["rerun_alive"] = res["ticks"], res.get("alive")  # states for re-judging
            entry["rerun_progress"] = res.get("progress")  # the rerun's second count (kept since 2026-11-21)
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
