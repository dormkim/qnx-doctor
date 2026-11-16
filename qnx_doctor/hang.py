"""Blocked-chain doctor: find a message-passing deadlock or priority chain on a QNX target, fix the source, prove it.

Loop (the AI never runs a command; it only returns edit_file actions as data):
  build (qcc) → image (mkqnximage) → boot + run on target (qd-target-exec) → pidin snapshot + TICK counts
  → wait graph judged by code (waitgraph) → AI reads graph + source + QNX docs → edit_file → rebuild → rerun.
«Solved» only when the rerun shows no cycle/chain AND the loop prints TICKs again.

A scenario directory holds *.c sources and run.sh (started by check.sh on the target); a sibling `common/`
directory (qd.h, snap.c, hi.c, check.sh) is copied along when present.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

from . import actions as act
from . import structure as st
from . import waitgraph as wg
from .runner import base_env, sdp_env, tail

QCC = ["qcc", "-Vgcc_ntox86_64"]
# Every send/receive call of a scenario program goes through common/qd_trace.c (message-structure recorder).
# Link-level, so the program's source — including an AI fix — cannot opt out (see qd_trace.c and structure.py).
TRACE_CALLS = [f"MsgSend{v}{r}" for v in ("", "nc", "sv", "svnc", "vs", "vsnc", "v", "vnc") for r in ("", "_r")] + \
    [f"MsgSendPulse{v}{r}" for v in ("", "Ptr") for r in ("", "_r")] + \
    [f"MsgReceive{v}{r}" for v in ("", "v", "Pulse") for r in ("", "_r")]
WRAP = ["-Wl," + ",".join(f"--wrap={c}" for c in TRACE_CALLS)]
MKIMG = ["mkqnximage", "--type=qemu", "--arch=x86_64", "--ssh-ident=none", "--noprompt", "--clean"]

HANG_SYSTEM = """You are qnx-doctor, fixing a hang in a QNX 8.0 message-passing program.
You get: the wait-for graph that code built from a pidin snapshot on the target (SEND/REPLY Blocked = peer pid),
the TICK counts of each role (a working loop prints TICK lines), and the program's source files.
Work step by step. Reply with exactly ONE JSON object per turn, nothing else:
  {"probe": {"argv": ["grep", "-n", "MsgSend", "D01/pingpong.c"]}}   read-only look (allowed: ls find cat head tail grep)
  {"search_docs": "words"}   searches the QNX 8.0 documentation (message passing, MsgSendPulse, priority inheritance, ...)
  {"diagnosis": {"cause_label": "one of: send_cycle | send_on_reply_path | fixed_priority_channel | other",
                 "cause": "short cause", "culprit": {"file": "path", "line": "the exact source line that made the cycle or chain"},
                 "pids": [pids from the graph of the processes in the cycle or chain],
                 "evidence": "graph edge or doc text that proves it", "doc_refs": ["doc path"],
                 "actions": [{"type": "edit_file", "path": "relative path", "find": "exact text", "replace": "new text"}]}}
  {"give_up": "why"}
cause_label: send_cycle = every member sends synchronously to the next before serving its own channel;
send_on_reply_path = a process that owes a reply sends synchronously to a process that waits (directly or through
others) for that reply (callback, relay closing the cycle); fixed_priority_channel = the server's channel does not
pass on the client's priority; other = none of these.
Rules: only edit_file actions, paths relative to the working directory, `find` must be copied exactly from the file.
Keep the program's intent: the same roles still talk to each other and the loop keeps running.
Use the QNX idiom for the problem (for example a non-blocking pulse instead of a synchronous send back, reply before
notifying, or letting the server inherit the client's priority). Adding a timeout or sleep that only hides the wait is not a fix.
Search the docs before deciding. Never invent text that is not in the file.
""" + st.RULES


def prepare(scen_dir: str) -> str:
    """Copy the scenario (and its sibling common/) into a fresh work directory; edits only ever touch the copy."""
    work = tempfile.mkdtemp(prefix="qd-hang-")
    name = os.path.basename(os.path.normpath(scen_dir))
    shutil.copytree(scen_dir, os.path.join(work, name))
    common = os.path.join(os.path.dirname(os.path.normpath(scen_dir)), "common")
    if os.path.isdir(common):
        shutil.copytree(common, os.path.join(work, "common"))
    for d, _, files in os.walk(work):  # comments (incl. answer-key markers of hand-written scenarios) never reach the AI
        for f in files:
            p = os.path.join(d, f)
            if f.endswith((".c", ".h")):
                t = open(p).read()
                open(p, "w").write(re.sub(r"/\*.*?\*/", "", t, flags=re.S))
    return work


def _sh(argv, cwd, env, timeout=900):
    p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).decode(errors="replace")


def build(work: str, name: str, env: dict):
    """qcc every .c into work/out (layout = /var/qd on the target). Returns (ok, log)."""
    out = os.path.join(work, "out")
    os.makedirs(os.path.join(out, name), exist_ok=True)
    jobs = []
    for f in ("snap", "hi"):
        if os.path.exists(os.path.join(work, "common", f + ".c")):
            jobs.append((os.path.join(out, f), os.path.join(work, "common", f + ".c"), []))
    trace = os.path.join(work, "common", "qd_trace.c")
    extra = [trace] + WRAP if os.path.exists(trace) else []
    for c in sorted(os.listdir(os.path.join(work, name))):
        if c.endswith(".c"):
            jobs.append((os.path.join(out, name, c[:-2]), os.path.join(work, name, c), extra))
    for dst, src, more in jobs:
        rc, log = _sh(QCC + ["-o", dst, src] + more, work, env)
        if rc != 0:
            return False, f"qcc {os.path.relpath(src, work)} failed:\n{tail(log, 20)}"
    shutil.copy(os.path.join(work, name, "run.sh"), os.path.join(out, name, "run.sh"))
    if os.path.exists(os.path.join(work, "common", "check.sh")):
        shutil.copy(os.path.join(work, "common", "check.sh"), os.path.join(out, "check.sh"))
    return True, "built"


def image(work: str, env: dict):
    """mkqnximage with every built file under /var/qd. Returns (ok, image dir, log)."""
    vm, out = os.path.join(work, "vm"), os.path.join(work, "out")
    os.makedirs(os.path.join(vm, "local", "snippets"), exist_ok=True)
    lines = []
    for d, _, files in os.walk(out):
        for f in sorted(files):
            p = os.path.join(d, f)
            lines.append(f"[perms=0755] /var/qd/{os.path.relpath(p, out)}={p}")
    open(os.path.join(vm, "local", "snippets", "data_files.custom"), "w").write("\n".join(lines) + "\n")
    rc, log = _sh(MKIMG, vm, env)
    ok = rc == 0 and os.path.exists(os.path.join(vm, "output", "ifs.bin"))
    return ok, vm, tail(log, 15)


def target(vm: str, name: str, env: dict):
    rc, out = _sh(["qd-target-exec", vm, f"/var/qd/hi /var/qd/check.sh {name}"], vm, env, timeout=600)
    return "QDDONE" in out, out


def observe(work: str, name: str, focus=None) -> dict:
    """Build, image, boot, run once; judge the snapshot. Pure data back for the timeline."""
    env = sdp_env(base_env())
    ok, log = build(work, name, env)
    if not ok:
        return {"stage": "build", "ok": False, "log": log}
    ok, vm, log = image(work, env)
    if not ok:
        return {"stage": "image", "ok": False, "log": log}
    ok, out = target(vm, name, env)
    shutil.rmtree(vm, ignore_errors=True)
    if not ok:
        return {"stage": "target", "ok": False, "log": tail(out, 20)}
    pidin, ticks = wg.split_check(out)
    threads = wg.parse(pidin)
    j = wg.judge(threads, focus)
    involved = _involved(j)
    lines = [l for l in pidin.splitlines() if any(l.strip().startswith(f"{p} ") for p in involved)]
    alive = len({t.pid for t in threads if f"var/qd/{name}/" in t.name})  # program processes still there
    structure = None
    if "=== MSGS ===" in out:  # harness with qd_trace (2026-11-16); older recordings have none
        args = st.parse_args(_section(out, "ARGS"), name)
        structure = st.build(args, st.parse_msgs(_section(out, "MSGS")), threads)
    return {"stage": "target", "ok": True, "judge": j, "graph": wg.describe(j), "ticks": ticks, "alive": alive,
            "healthy": j["kind"] == "none" and sum(ticks.values()) > 0, "pidin_lines": lines, "structure": structure}


def _section(out: str, name: str) -> str:
    return out.split(f"=== {name} ===", 1)[-1].split("===", 1)[0] if f"=== {name} ===" in out else ""


def _involved(j):
    if j["kind"] == "deadlock":
        return {m["pid"] for c in j["cycles"] for m in c} | {b["pid"] for b in j["behind"]}
    if j["kind"] == "priority_chain":
        return {x for c in j["chains"] for x in (c["waiter"]["pid"], c["server"]["pid"], *[r[0] for r in c["running"]])}
    return set()


def sources(work: str, name: str) -> str:
    parts = []
    for d in (name, "common"):
        base = os.path.join(work, d)
        for f in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            if f.endswith((".c", ".h", ".sh")):
                parts.append(f"--- {d}/{f} ---\n" + open(os.path.join(base, f)).read())
    return "\n".join(parts)


def context(work, name, obs, tried):
    lines = [f"Program: {name} (sources below, working directory {work})",
             "Wait graph (code): " + obs["graph"],
             "pidin lines of the processes involved:\n" + "\n".join(obs["pidin_lines"]),
             "TICK counts per role log (0 = loop not running): " + json.dumps(obs["ticks"]),
             "Sources:\n" + sources(work, name)]
    for t in tried:
        lines.append(f"Already tried: {json.dumps(t['actions'])} -> {t['result']}")
    return "\n\n".join(lines)


CAUSE_LABELS = ("send_cycle", "send_on_reply_path", "fixed_priority_channel", "other")


def checked_claims(work, payload):
    """Keep the AI's words only where code can confirm them: a closed cause label, and a culprit line that is
    really in that file of the working copy. Recorded for scoring; it does not change «fixed»."""
    label = payload.get("cause_label")
    c = payload.get("culprit") or {}
    path = os.path.realpath(os.path.join(work, str(c.get("file", ""))))
    line = str(c.get("line", "")).strip()
    ok = (bool(line) and path.startswith(os.path.realpath(work) + os.sep) and os.path.isfile(path)
          and line in open(path, errors="replace").read())
    return {"cause_label": label if label in CAUSE_LABELS else "unlisted", "culprit_in_source": ok}


def pids_checked(payload, obs):
    """The AI's pids are kept only if every one is a process the code found in the cycle/chain (pid cross-check)."""
    said = payload.get("pids")
    if not isinstance(said, list) or not said:
        return None
    try:
        return {int(p) for p in said} <= _involved(obs["judge"])
    except (TypeError, ValueError):
        return False


def apply_fix(scen_dir, acts):
    """Fresh copy + edit_file actions only, on the program's C sources (not run.sh, not the harness). (work, error)."""
    work = prepare(scen_dir)
    if any(a.get("type") != "edit_file" for a in acts):
        return work, "rejected: only edit_file is allowed for a hang fix"
    why = st.static_reject(acts)
    if why:
        return work, why
    orig = {a.get("path"): open(os.path.join(work, a["path"]), errors="replace").read()
            for a in acts if os.path.isfile(os.path.join(work, str(a.get("path", ""))))}
    try:
        act.apply({"argv": ["true"], "cwd": "."}, acts, work)
    except act.Rejected as e:
        return work, f"rejected: {e}"
    for path, text in orig.items():
        if st.receive_removed(text, open(os.path.join(work, path), errors="replace").read()):
            return work, f"{st.STATIC} {path}: the fix removes a receive call (a receiver must keep reading its channel)"
    return work, None


def diff(work_a, work_b, name):
    rc, out = _sh(["diff", "-ru", os.path.join(work_a, name), os.path.join(work_b, name)], work_a, base_env(), 30)
    out = out.replace(work_a + "/", "a/").replace(work_b + "/", "b/")
    return re.sub(r"^((?:---|\+\+\+) \S+)\t.*$", r"\1", out, flags=re.M)[:4000]  # drop file timestamps
