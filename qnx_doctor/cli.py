"""qnx-doctor command line.

  python3 -m qnx_doctor.cli bench <dir-or-files...> --mode rules|ai --out runs/x.jsonl
  python3 -m qnx_doctor.cli diagnose <scenario.json> [--no-ai]
  python3 -m qnx_doctor.cli index            # build the local QNX docs index once
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


def main():
    ap = argparse.ArgumentParser(prog="qnx-doctor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bench"); b.add_argument("paths", nargs="+"); b.add_argument("--mode", choices=["rules", "ai"], default="ai"); b.add_argument("--out")
    d = sub.add_parser("diagnose"); d.add_argument("scenario"); d.add_argument("--no-ai", action="store_true")
    sub.add_parser("index")
    a = ap.parse_args()
    sdp = base_env()["QNX_SDP"]
    if a.cmd == "index":
        from .docs import build
        print(len(build(sdp)), "docs indexed"); return
    index = None
    use_ai = (a.cmd == "bench" and a.mode == "ai") or (a.cmd == "diagnose" and not a.no_ai)
    if use_ai:
        from .docs import Index
        index = Index(sdp)
    scen = _scenarios(a.paths if a.cmd == "bench" else [a.scenario])
    out = open(a.out, "a") if getattr(a, "out", None) else None
    solved = 0
    for s in scen:
        r = diagnose(s, use_ai=use_ai, index=index)
        r["mode"] = "ai" if use_ai else "rules"
        solved += bool(r.get("solved"))
        print(json.dumps({k: r.get(k) for k in ("id", "mode", "solved", "by", "cause", "seconds")}, ensure_ascii=False), flush=True)
        if out:
            out.write(json.dumps(r, ensure_ascii=False) + "\n"); out.flush()
    print(f"solved (proven by rerun): {solved}/{len(scen)}")


if __name__ == "__main__":
    sys.exit(main())
