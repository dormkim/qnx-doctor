"""qnx-doctor command line.

  python3 -m qnx_doctor.cli bench <dir-or-files...> --mode rules|ai --out runs/x.jsonl
  python3 -m qnx_doctor.cli diagnose <scenario.json> [--no-ai]
  python3 -m qnx_doctor.cli index            # build the local QNX docs index once
  python3 -m qnx_doctor.cli run [--no-ai] -- <cmd...>        # diagnose a failing build/boot command (fixes tried on a copy of .)
  python3 -m qnx_doctor.cli hang [name|pid] --pidin FILE     # read-only: wait graph of a pidin capture
  python3 -m qnx_doctor.cli hang [name|pid] --live "ssh root@target" [--src DIR] [--out runs/x.jsonl]
                                             # read-only: pidin + pidin arg from a running target (no harness)
  python3 -m qnx_doctor.cli hang [name|pid] --scenario DIR [--no-ai] [--out runs/x.jsonl]
                                             # build → target → graph → AI fix (edit_file) → rebuild → rerun
"""
import argparse
import glob
import json
import os
import sys

from .doctor import diagnose
from .runner import base_env


def _scenarios(paths):
    out = []
    for p in paths:
        files = sorted(glob.glob(os.path.join(p, "*.json"))) if os.path.isdir(p) else [p]
        for f in files:
            s = json.load(open(f))
            if "spec" in s:  # recorded-only scenarios have no spec
                out.append(s)
    return out


def _run_scenario(a):
    argv = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not argv:
        sys.exit("usage: qnx-doctor run -- <command...>")
    return [{"id": "run", "copy_from": os.getcwd(), "spec": {"argv": argv, "cwd": ".", "timeout": 900}}]


def _hang(a):
    from . import waitgraph as wg
    if a.pidin:
        j = wg.judge(wg.parse(open(a.pidin).read()), a.target)
        print(wg.describe(j)); print(json.dumps(j, ensure_ascii=False))
        return 0 if j["kind"] == "none" else 3
    if a.live:
        from . import live
        raw = live.capture(a.live)
        r = live.check(raw, a.target, a.src)
        print(live.report(r))
        if a.out:  # the raw capture is kept next to the verdict, so the graph can be checked by hand
            open(a.out + ".raw.txt", "w").write(raw)
            open(a.out, "a").write(json.dumps({"mode": "live", **r}, ensure_ascii=False) + "\n")
        return 0 if r["kind"] == "none" else 3
    if not a.scenario:
        sys.exit("hang needs --pidin FILE, --live TRANSPORT or --scenario DIR")
    from .hangdoctor import diagnose_hang
    index = None
    if not a.no_ai:
        from .docs import Index
        index = Index(base_env()["QNX_SDP"])
    out = open(a.out, "a") if a.out else None
    for d in a.scenario:
        r = diagnose_hang(d, use_ai=not a.no_ai, index=index, focus=a.target)
        r["mode"] = "code" if a.no_ai else "ai"
        print(json.dumps({k: r.get(k) for k in ("id", "mode", "detected", "solved", "by", "cause")}, ensure_ascii=False), flush=True)
        if out:
            out.write(json.dumps(r, ensure_ascii=False) + "\n"); out.flush()
    return 0


def main():
    ap = argparse.ArgumentParser(prog="qnx-doctor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bench"); b.add_argument("paths", nargs="+"); b.add_argument("--mode", choices=["rules", "ai", "ai-only"], default="ai"); b.add_argument("--out")
    d = sub.add_parser("diagnose"); d.add_argument("scenario"); d.add_argument("--no-ai", action="store_true")
    sub.add_parser("index")
    r = sub.add_parser("run"); r.add_argument("--no-ai", action="store_true"); r.add_argument("cmd", nargs=argparse.REMAINDER)
    h = sub.add_parser("hang"); h.add_argument("target", nargs="?"); h.add_argument("--pidin"); h.add_argument("--scenario", nargs="+")
    h.add_argument("--live", metavar="TRANSPORT", help='command that runs one shell line on the target, e.g. "ssh root@10.0.2.15"')
    h.add_argument("--src", help="with --live: source tree to point at the message-passing calls of the processes involved")
    h.add_argument("--no-ai", action="store_true"); h.add_argument("--out")
    v = sub.add_parser("verify", help="judge a hang fix written by anyone: accept, reject or review (no model)")
    v.add_argument("scenario"); v.add_argument("patch", help="unified diff against the scenario, or JSON edit_file actions")
    v.add_argument("--out", help="append the row as JSON")
    a = ap.parse_args()
    if a.cmd == "hang":
        return _hang(a)
    if a.cmd == "verify":
        from .verify import verify
        row = verify(a.scenario, a.patch)
        print(f"{row['verdict'].upper()}: " + ("; ".join(row["why"]) or "the stopped loop runs again with the same message structure"))
        print(json.dumps({k: row.get(k) for k in ("id", "patch", "verdict", "liveness_only", "structure_rule")}), flush=True)
        if a.out:
            with open(a.out, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return {"accept": 0, "review": 3}.get(row["verdict"], 1)
    sdp = base_env()["QNX_SDP"]
    if a.cmd == "index":
        from .docs import build
        print(len(build(sdp)), "docs indexed"); return
    index = None
    use_ai = (a.cmd == "bench" and a.mode in ("ai", "ai-only")) or (a.cmd in ("diagnose", "run") and not a.no_ai)
    use_rules = not (a.cmd == "bench" and a.mode == "ai-only")
    if use_ai:
        from .docs import Index
        index = Index(sdp)
    scen = _run_scenario(a) if a.cmd == "run" else _scenarios(a.paths if a.cmd == "bench" else [a.scenario])
    out = open(a.out, "a") if getattr(a, "out", None) else None
    solved = 0
    for s in scen:
        r = diagnose(s, use_ai=use_ai, index=index, use_rules=use_rules)
        r["mode"] = a.mode if a.cmd == "bench" else ("ai" if use_ai else "rules")
        solved += bool(r.get("solved"))
        print(json.dumps({k: r.get(k) for k in ("id", "mode", "solved", "by", "cause", "seconds")}, ensure_ascii=False), flush=True)
        if out:
            out.write(json.dumps(r, ensure_ascii=False) + "\n"); out.flush()
    print(f"solved (proven by rerun): {solved}/{len(scen)}")


if __name__ == "__main__":
    sys.exit(main())
