"""The diagnose loop. «Solved» is only ever decided by re-running the user's command (fix proven by rerun)."""
import json
import os
import shutil
import subprocess
import tempfile
import time

from . import actions as act
from . import rules
from .runner import build_env, expand, run, tail

CLEAN_KEYS = ("PATH", "QNX_HOST", "QNX_TARGET", "LD_LIBRARY_PATH", "QEMU_MODULE_DIR")


def setup(scenario):
    work = tempfile.mkdtemp(prefix=f"qd-{scenario['id']}-")
    env = build_env({})
    if scenario.get("copy_from"):  # `qnx-doctor run`: fixes are tried on a copy, the user's tree is never edited
        shutil.copytree(scenario["copy_from"], work, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
    if scenario.get("setup"):
        subprocess.run(["bash", "-c", scenario["setup"]], cwd=work, env=env, capture_output=True, timeout=600)
    return work


def context_text(spec, res, work, tried):
    env = build_env(spec)
    shown = {k: env.get(k, "(unset)") for k in CLEAN_KEYS}
    cwd = os.path.join(work, spec.get("cwd", "."))
    try:
        listing = ", ".join(sorted(os.listdir(cwd))[:40])
    except OSError:
        listing = "?"
    lines = [
        "Command (as run): " + " ".join(expand(spec["argv"], env)),
        f"Working directory: {cwd} (contains: {listing})",
        "SDP environment sourced: " + ("yes" if spec.get("source_sdp") else "no"),
        "QNX SDP install: " + env["QNX_SDP"],
        "Relevant environment: " + json.dumps(shown),
        "Success means: " + json.dumps(spec.get("success", {"exit": 0})),
        f"Result: {res.reason}",
        "Output (tail):\n" + tail(res.output, 50),
    ]
    for t in tried:
        lines.append(f"Already tried: {json.dumps(t['actions'])} -> {t['result']}")
    return "\n".join(lines)


def attempt(scenario, acts):
    work = setup(scenario)
    try:
        spec = act.apply(scenario["spec"], acts, work)
    except act.Rejected as e:
        shutil.rmtree(work, ignore_errors=True)
        return None, f"rejected: {e}"
    res = run(spec, work)
    shutil.rmtree(work, ignore_errors=True)
    return res, ("SOLVED (rerun ok)" if res.ok else f"still failing: {res.reason}; {tail(res.output, 6)}")


def diagnose(scenario, use_ai=True, index=None, max_fixes=2, use_rules=True):
    t0 = time.time()
    timeline, tried = [], []
    work = setup(scenario)
    spec = scenario["spec"]
    first = run(spec, work)
    timeline.append({"kind": "symptom", "reason": first.reason, "out": tail(first.output, 8)})
    if first.ok:
        shutil.rmtree(work, ignore_errors=True)
        return {"id": scenario["id"], "solved": None, "note": "command did not fail", "timeline": timeline}
    env = build_env(spec)
    # 1) rule table (works without AI)
    sug = rules.suggest(expand(spec["argv"], env), first.output) if use_rules else None
    if sug:
        cause, acts, why = sug
        res, msg = attempt(scenario, acts)
        timeline.append({"kind": "rule", "cause": cause, "why": why, "actions": acts, "result": msg})
        tried.append({"actions": acts, "result": msg})
        if res and res.ok:
            shutil.rmtree(work, ignore_errors=True)
            return {"id": scenario["id"], "solved": True, "by": "rules", "cause": cause, "actions": acts,
                    "seconds": round(time.time() - t0), "timeline": timeline}
    if not use_ai:
        shutil.rmtree(work, ignore_errors=True)
        return {"id": scenario["id"], "solved": False, "by": "rules", "seconds": round(time.time() - t0), "timeline": timeline}
    # 2) AI: look around, read docs, propose a fix; code re-runs to prove it
    from . import ai
    for _ in range(max_fixes):
        kind, payload, _msgs = ai.think(context_text(spec, first, work, tried), os.path.join(work, spec.get("cwd", ".")),
                                        build_env(spec), index, timeline)
        if kind == "give_up":
            timeline.append({"kind": "give_up", "why": payload})
            shutil.rmtree(work, ignore_errors=True)
            return {"id": scenario["id"], "solved": False, "by": "ai", "explained": payload,
                    "seconds": round(time.time() - t0), "timeline": timeline}
        acts = payload.get("actions", [])
        res, msg = attempt(scenario, acts)
        timeline.append({"kind": "ai_fix", "cause": payload.get("cause"), "evidence": payload.get("evidence"),
                         "doc_refs": payload.get("doc_refs"), "actions": acts, "result": msg})
        tried.append({"actions": acts, "result": msg})
        if res and res.ok:
            shutil.rmtree(work, ignore_errors=True)
            return {"id": scenario["id"], "solved": True, "by": "ai", "cause": payload.get("cause"), "actions": acts,
                    "seconds": round(time.time() - t0), "timeline": timeline}
    shutil.rmtree(work, ignore_errors=True)
    return {"id": scenario["id"], "solved": False, "by": "ai", "seconds": round(time.time() - t0), "timeline": timeline}
