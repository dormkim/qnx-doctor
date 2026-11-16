"""Attack the hang verifier on the real target with shortcut «fixes» (dev pool only — never held-out or sealed).

For one deadlock ring (every member sends first) and one priority chain from the dev pool, build fixes by plain
text edits, apply each to a fresh copy, rebuild with qcc, boot, rerun, and judge with hangdoctor.verdict:
  real    pulse back / channel without _NTO_CHF_FIXED_PRIORITY            -> must be fixed
  fake    rewire run.sh, one member stops sending, client stops sending,
          CPU-load threads removed, CPU load lowered                       -> must be rejected
Prints one row per fix: expected, fixed, alive-again (liveness only), reasons. States only (QNX licence 4.2(i)).

  python3 bench/fake_fix_check.py --pool /tmp/qd_dev --out runs/fake_fix.jsonl
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


def src(pool, sid):
    c = [f for f in os.listdir(os.path.join(pool, sid)) if f.endswith(".c")][0]
    return f"{sid}/{c}", open(os.path.join(pool, sid, c)).read(), open(os.path.join(pool, sid, "run.sh")).read()


def ring_fixes(pool, sid, lab):
    path, s, run = src(pool, sid)
    send = re.search(r"    qd_send\((\w+), n\);\n    int \w+ = qd_receive", s)
    c = send[1]
    line = f"    qd_send({c}, n);"
    first = lab["members"][0]
    peer_line = next(l for l in run.splitlines() if f" {first} " in l and l.startswith("/var/qd"))
    return [("real: pulse to the next member", True, [{"type": "edit_file", "path": path, "find": line, "replace": f"    MsgSendPulse({c}, -1, 1, n);"}]),
            ("fake: run.sh rewired", False, [{"type": "edit_file", "path": f"{sid}/run.sh", "find": peer_line, "replace": peer_line.replace(f" {first} ", f" {first}x ", 1)}]),
            ("fake: one member stops sending", False, [{"type": "edit_file", "path": path, "find": line, "replace": f"    if (strcmp(me, \"{first}\")) qd_send({c}, n);"}]),
            ("fake: every member stops sending", False, [{"type": "edit_file", "path": path, "find": line, "replace": f"    (void){c};"}])]


def chain_fixes(pool, sid, lab):
    path, s, _ = src(pool, sid)
    out = [("real: channel inherits the client's priority", True,
            [{"type": "edit_file", "path": path, "find": "ChannelCreate(_NTO_CHF_FIXED_PRIORITY)", "replace": "ChannelCreate(0)"}])]
    out.append(("fake: CPU-load threads removed", False, [{"type": "edit_file", "path": path, "find": "for (int i = 0; i < 2; i++) pthread_create",
                                                              "replace": "for (int i = 0; i < 0; i++) pthread_create"}]))
    mid = re.search(r"setprio\(0, (\d+)\);\n  pthread_t t\[2\]", s)
    out.append(("fake: CPU load lowered", False, [{"type": "edit_file", "path": path, "find": mid[0], "replace": mid[0].replace(f"setprio(0, {mid[1]})", "setprio(0, 1)")}]))
    cli = re.search(r"    qd_send\((\w+), n\);\n    qd_tick\(me, n\);\n    usleep", s)
    if cli and "ConnectAttach" in s[max(0, cli.start() - 600):cli.start()]:
        out.append(("fake: client stops sending", False, [{"type": "edit_file", "path": path, "find": cli[0], "replace": cli[0].replace(f"qd_send({cli[1]}, n);", f"(void){cli[1]};")}]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True); ap.add_argument("--out", required=True); ap.add_argument("--only")
    a = ap.parse_args()
    labels = json.load(open(os.path.join(a.pool, "labels.json")))
    ring = next(k for k, v in labels.items() if v["kind"] == "deadlock" and "each member makes" in (v.get("culprit") or ""))
    chain = next(k for k, v in labels.items() if v["kind"] == "priority_chain")
    with open(a.out, "w") as out:
        for sid, maker in ((ring, ring_fixes), (chain, chain_fixes)):
            if a.only and a.only not in (sid, maker.__name__):
                continue
            work = hang.prepare(os.path.join(a.pool, sid))
            first = hang.observe(work, sid)
            print(json.dumps({"id": sid, "first": first.get("judge", {}).get("kind"), "ticks": first.get("ticks"), "alive": first.get("alive")}), flush=True)
            shutil.rmtree(work, ignore_errors=True)
            for name, want, acts in maker(a.pool, sid, labels[sid]):
                fixed, err = hang.apply_fix(os.path.join(a.pool, sid), acts)
                res = {} if err else hang.observe(fixed, sid)
                v = {"fixed": False, "live": None, "structure": [err]} if err else verdict(first, res)
                v["rerun"] = {"stage": res.get("stage"), "ok": res.get("ok"), "kind": (res.get("judge") or {}).get("kind"),
                              "ticks": res.get("ticks"), "alive": res.get("alive"), "log": (res.get("log") or "")[-300:]}
                shutil.rmtree(fixed, ignore_errors=True)
                row = {"id": sid, "fix": name, "expected_fixed": want, **v, "ok": v["fixed"] == want}
                out.write(json.dumps(row) + "\n"); out.flush()
                print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
