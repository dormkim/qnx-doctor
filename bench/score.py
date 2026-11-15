"""Score a bench run against the sealed truth. The doctor never reads `truth`; only this file does.

  python3 bench/score.py tests/sealed runs/sealed_rules.jsonl runs/sealed_ai-only.jsonl runs/sealed_ai.jsonl
Columns: solved (proven by re-run) · claimed-but-broken (must be 0) · cause matches truth (exact label, rules only)
"""
import glob
import json
import os
import sys


def main(sealed, runs):
    truth = {}
    for f in glob.glob(os.path.join(sealed, "X*.json")):
        s = json.load(open(f))
        if "spec" in s:
            truth[s["id"]] = s.get("truth", {}).get("cause")
    print(f"scenarios scored: {len(truth)}")
    print("| run | solved (re-run proven) | claimed but broken | cause label = truth |")
    print("|---|---|---|---|")
    for rp in runs:
        rows = [json.loads(l) for l in open(rp) if l.strip()]
        rows = [r for r in rows if r.get("id") in truth]
        solved = sum(1 for r in rows if r.get("solved") is True)
        broken = sum(1 for r in rows if r.get("solved") is True and r.get("verified") is False)
        match = sum(1 for r in rows if r.get("cause") and r.get("cause") == truth[r["id"]])
        print(f"| {os.path.basename(rp)} | {solved}/{len(truth)} | {broken} | {match}/{len(truth)} |")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
