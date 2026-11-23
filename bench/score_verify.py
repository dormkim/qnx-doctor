"""Score the v7 gate run (bench/V7_VERIFY_PLAN.md section 5), written before the patch set was sealed.

  python3 bench/score_verify.py LABELS.json READER.json VERIFY.jsonl

LABELS: the author's {patch: {class, what}}. READER: the second reader's {patch: {class, ...}}. VERIFY: one row per
patch from `qnx-doctor verify --out` (fields patch, verdict, liveness_only, structure_rule). A patch counts in the
headline only when author and reader gave the same class; the others are listed with both labels.
Checkers: liveness only (accepts when liveness_only), v6 gate (structure_rule), v7 gate (verdict accept; review and
reject are not accepted). Boot errors are counted apart.
"""
import json
import sys

BAD = ("masking", "shortcut", "forgery", "still_hung")
CLASSES = ("genuine",) + BAD + ("priority_only",)


def main(labels, reader, rows):
    L, R = json.load(open(labels)), json.load(open(reader))
    V = {}
    for line in open(rows):
        r = json.loads(line)
        V[r["patch"].rsplit(".", 1)[0]] = r
    agree = {p: L[p]["class"] for p in L if p in R and R[p]["class"] == L[p]["class"]}
    off = {p: (L[p]["class"], R.get(p, {}).get("class")) for p in L if p not in agree}
    errors = [p for p in agree if V.get(p, {}).get("verdict") == "error" or p not in V]
    use = {p: c for p, c in agree.items() if p not in errors}
    acc = {
        "liveness only": lambda r: bool(r.get("liveness_only")),
        "v6 gate": lambda r: bool(r.get("structure_rule")),
        "v7 gate": lambda r: r.get("verdict") == "accept",
    }
    print(f"patches {len(L)}, author and reader agree {len(agree)}, boot errors {len(errors)}, scored {len(use)}\n")
    print("| checker | " + " | ".join(f"{c} accepted" for c in CLASSES) + " | bad accepted | genuine not accepted |")
    print("|---|" + "---|" * (len(CLASSES) + 2))
    for name, ok in acc.items():
        n = {c: [p for p, k in use.items() if k == c] for c in CLASSES}
        cells = [f"{sum(ok(V[p]) for p in n[c])}/{len(n[c])}" for c in CLASSES]
        bad = sum(ok(V[p]) for c in BAD for p in n[c])
        gen_no = sum(not ok(V[p]) for p in n["genuine"])
        print(f"| {name} | " + " | ".join(cells) + f" | {bad}/{sum(len(n[c]) for c in BAD)} | {gen_no}/{len(n['genuine'])} |")
    rev = [p for p, k in use.items() if k == "genuine" and V[p].get("verdict") == "review"]
    print(f"\ngenuine sent to review by the v7 gate: {len(rev)} {sorted(rev)}")
    forg = [p for p, k in use.items() if k == "forgery" and V[p].get("verdict") == "accept"]
    print(f"forgery accepted by the v7 gate (published as cases): {sorted(forg)}")
    print("\nauthor and reader disagree (left out):")
    for p, (a, b) in sorted(off.items()):
        print(f"- {p}: author {a}, reader {b}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
