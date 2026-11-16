"""Score hang runs against an answer key. Only this file reads labels.json; the doctor and the baseline never do.

  python3 bench/score_hang.py LABELS.json runs/a.jsonl [runs/b.jsonl ...]
Per run: kind found = label kind, per kind; false alarms (label none, reported a hang); missed (label is a hang,
reported none); fixed (proven by rerun); false fixes (claimed fixed on a scenario whose label is none — must be 0).
States only, no time numbers (QNX licence 4.6(i)).
"""
import json
import os
import sys

KINDS = ("deadlock", "priority_chain", "missing_reply", "none")


# Expected closed cause label (qnx_doctor.hang.CAUSE_LABELS) from the answer key. Hand-written set by id; D03 is
# a cycle of two senders (server→logger, logger→server) so both cycle labels are accepted there.
SEALED_CAUSE = {"D01": {"send_cycle"}, "D02": {"send_cycle"}, "D03": {"send_cycle", "send_on_reply_path"},
                "D04": {"send_on_reply_path"}, "D05": {"fixed_priority_channel"}}


def expected_cause(sid, lab):
    if sid in SEALED_CAUSE:
        return SEALED_CAUSE[sid]
    if lab.get("gen_version", 1) >= 2:  # generator v2 writes the cause label into the answer key
        return {lab["cause"]} if lab.get("cause") else set()
    if lab["kind"] == "priority_chain":
        return {"fixed_priority_channel"}
    if lab["kind"] == "deadlock":  # generator: all members send first, or a relay closes the cycle
        return {"send_cycle"} if "each member makes" in (lab.get("culprit") or "") else {"send_on_reply_path"}
    return set()


def load_labels(path):
    return {k: v for k, v in json.load(open(path)).items() if not k.startswith("_")}


def score(labels, rows):
    rows = {r["id"]: r for r in rows if r.get("id") in labels}
    s = {"n": {k: 0 for k in KINDS}, "hit": {k: 0 for k in KINDS}, "false_alarm": 0, "missed": 0, "fixed": 0,
         "false_fix": 0, "harness": 0, "faults": 0, "label_ok": 0, "labelled": 0}
    for sid, lab in labels.items():
        k = lab["kind"]
        s["n"][k] += 1
        s["faults"] += k != "none"
        r = rows.get(sid)
        if r is None or r.get("detected") is None and r.get("by") == "harness":
            s["harness"] += 1
            continue
        got = r.get("detected")
        s["hit"][k] += got == k
        s["false_alarm"] += k == "none" and got not in ("none", None)
        s["missed"] += k != "none" and got in ("none", None)
        s["fixed"] += r.get("solved") is True and k != "none"
        s["false_fix"] += r.get("solved") is True and k == "none"
        if r.get("cause_label"):  # AI arm, only where a fix was proven (the label of the fix that worked)
            s["labelled"] += 1
            s["label_ok"] += r["cause_label"] in expected_cause(sid, lab)
    return s


def table(labels, runs):
    out = ["| run | " + " | ".join(f"{k} found" for k in KINDS) + " | false alarm | missed | fixed (rerun) | false fix | cause label ok | harness fail |",
           "|---|" + "---|" * (len(KINDS) + 6)]
    for rp in runs:
        s = score(labels, [json.loads(l) for l in open(rp) if l.strip()])
        cells = [f"{s['hit'][k]}/{s['n'][k]}" for k in KINDS]
        out.append(f"| {os.path.basename(rp)} | " + " | ".join(cells) +
                   f" | {s['false_alarm']}/{s['n']['none']} | {s['missed']}/{s['faults']} | {s['fixed']}/{s['faults']} | {s['false_fix']}"
                   f" | {str(s['label_ok']) + '/' + str(s['labelled']) if s['labelled'] else '-'} | {s['harness']} |")
    return "\n".join(out)


if __name__ == "__main__":
    print(table(load_labels(sys.argv[1]), sys.argv[2:]))
