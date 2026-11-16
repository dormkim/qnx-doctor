"""Same fix, several reruns: does the verdict stay the same? (dev pool only — never held-out or sealed.)

For each named (scenario, fix) pair: boot the original once, then apply the same hand-written fix to a fresh copy
and rerun it N times, one QEMU guest at a time. Each rerun is judged with hangdoctor.verdict. A row per rerun keeps
the code's kind, the chain's runnable middle threads (name + priority), and the verdict. States only — no time or
performance numbers (QNX licence 4.2(i)).

Why (2026-11-17): on the v2 held-out run two naive fixes broke the ring but the rerun showed a priority chain, and
one earlier rerun came back with damaged output. A verifier whose verdict changes between reruns of the same fix
cannot be trusted, so this is the acceptance check for the harness: 3 reruns in a row, the same verdict.

  python3 bench/stability_check.py --pool /tmp/qd_dev2 --n 3 --out runs/stab/x.jsonl [--only SID]
"""
import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qnx_doctor import hang  # noqa: E402
from qnx_doctor.hangdoctor import verdict  # noqa: E402


def _files(pool, sid):
    return {f"{sid}/{f}": open(os.path.join(pool, sid, f)).read() for f in sorted(os.listdir(os.path.join(pool, sid))) if f.endswith(".c")}


def _find(pool, sid, pattern):
    for path, s in _files(pool, sid).items():
        m = re.search(pattern, s)
        if m:
            return path, m
    raise LookupError(f"{sid}: {pattern}")


def ring_mode_by_name(pool, sid):
    """Like the naive fixes that later showed a chain (v2 held-out): the run-time mode bit is replaced by a name
    order, so exactly one member of a 2-ring sends first."""
    path, m = _find(pool, sid, r"  int (\w+) = \(.*>> a\) & 1;")
    return [{"type": "edit_file", "path": path, "find": m[0], "replace": f"  int {m[1]} = strcmp(me, nx) < 0; (void)a;"}]


def ring_pulse(pool, sid):
    """Our usual fix: the send-first member notifies the next with a pulse instead of a blocking send."""
    path, m = _find(pool, sid, r"    if \((\w+)\) qd_send\((\w+), n\);")
    return [{"type": "edit_file", "path": path, "find": m[0], "replace": f"    if ({m[1]}) MsgSendPulse({m[2]}, -1, 1, n);"}]


def chain_inherit(pool, sid):
    path, _ = _find(pool, sid, r"ChannelCreate\(_NTO_CHF_FIXED_PRIORITY\)")
    return [{"type": "edit_file", "path": path, "find": "ChannelCreate(_NTO_CHF_FIXED_PRIORITY)", "replace": "ChannelCreate(0)"}]


def flags_inherit(pool, sid):
    for f in sorted(os.listdir(os.path.join(pool, sid))):
        if f.endswith(".h") and "_NTO_CHF_FIXED_PRIORITY" in open(os.path.join(pool, sid, f)).read():
            return [{"type": "edit_file", "path": f"{sid}/{f}", "find": " | _NTO_CHF_FIXED_PRIORITY", "replace": ""}]
    raise LookupError(sid)


def reply_then_pulse(pool, sid):
    path, m = _find(pool, sid, r"    if \((\w+) == -1\) \1 = qd_open\(nx\);\n    qd_send\(\1, (\w+)\.app\.v\);\n    (MsgReply\(\w+, EOK, .*\);)\n")
    c, msg, reply = m[1], m[2], m[3]
    return [{"type": "edit_file", "path": path, "find": m[0],
             "replace": f"    {reply}\n    if ({c} == -1) {c} = qd_open(nx);\n    MsgSendPulse({c}, -1, 1, {msg}.app.v);\n"}]


def reply_hello(pool, sid):
    path, m = _find(pool, sid, r"    int (\w+) = qd_receive\(at->chid, &\w+\);\n    if \(\1 <= 0\) continue;\n    if \(.*continue; \}")
    line = m[0].splitlines()[-1]
    return [{"type": "edit_file", "path": path, "find": line, "replace": line.replace("continue; }", f"MsgReply({m[1]}, EOK, NULL, 0); continue; }}")}]


def as_is(pool, sid):
    return []


# dev v2 (seeds2.json «dev»): two confounder rings like the two held-out cases, one plain chain, one healthy run,
# and the three QNX trap kinds of traps.py (2026-11-17).
CASES = [("t54e3fe", "ring_mode_by_name", ring_mode_by_name), ("t54e3fe", "ring_pulse", ring_pulse),
         ("t6dd334", "ring_pulse", ring_pulse), ("t151018", "chain_inherit", chain_inherit), ("tcb2750", "as_is", as_is),
         ("t363df3", "reply_then_pulse", reply_then_pulse), ("t5e594f", "flags_inherit", flags_inherit),
         ("t9273af", "reply_hello", reply_hello)]


def summary(res):
    j = res.get("judge") or {}
    mids = sorted({(n.split("/")[-1], p) for c in j.get("chains", []) for _, n, p in c["running"]})
    return {"stage": res.get("stage"), "ok": res.get("ok"), "kind": j.get("kind"), "chain_middle": mids,
            "ticks_zero": sorted(k for k, v in (res.get("ticks") or {}).items() if v == 0), "alive": res.get("alive"),
            "msgs": bool(res.get("structure")), "runnable": res.get("runnable")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=3); ap.add_argument("--only")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    firsts = {}
    with open(a.out, "w") as out:
        for sid, name, maker in CASES:
            if a.only and a.only not in (sid, name):
                continue
            if sid not in firsts:
                work = hang.prepare(os.path.join(a.pool, sid))
                firsts[sid] = hang.observe(work, sid)
                shutil.rmtree(work, ignore_errors=True)
                row = {"id": sid, "fix": None, "run": 0, **summary(firsts[sid])}
                out.write(json.dumps(row) + "\n"); out.flush(); print(json.dumps(row), flush=True)
            acts = maker(a.pool, sid)
            for i in range(1, a.n + 1):
                fixed, err = hang.apply_fix(os.path.join(a.pool, sid), acts)
                res = {} if err else hang.observe(fixed, sid)
                shutil.rmtree(fixed, ignore_errors=True)
                v = {"fixed": False, "live": None, "structure": [err]} if err else verdict(firsts[sid], res)
                row = {"id": sid, "fix": name, "run": i, **summary(res), "fixed": v["fixed"], "live": v["live"], "why": v["structure"]}
                out.write(json.dumps(row) + "\n"); out.flush(); print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
