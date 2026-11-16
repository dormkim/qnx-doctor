#!/usr/bin/env bash
# 2026-11-16 second measurement, with the «same message structure» verifier (structure.py + qd_trace.c).
#  A. v1 sets (sealed 7 + held-out 20): the fixes recorded on the first run, re-judged (no new AI call).
#  B. v2 held-out 30 (sealed f19d090): first run ever — code only, then AI ∥ naive, both told the same rules.
# The v2 pool is regenerated and its hashes must match tests/gen_hang/sealed2.json, or nothing runs.
# Server only, detached; writes $S/state.$PHASE (A / B-code / B-ai / done / fail:<why>). States only (QNX 4.2(i)).
set -u
set -a; . ~/.config/qnx-doctor/env; set +a
cd ~/personal/qnx-doctor
S=runs/st_1116; mkdir -p $S; PY=.venv/bin/python
PHASE=${1:-all}   # A | B | all (state file per phase, so A and B can run side by side)
fail() { echo "fail:$1" > $S/state.$PHASE; exit 1; }

if [ "$PHASE" != B ]; then
echo A > $S/state.$PHASE
python3 tests/gen_hang/gen.py --pool heldout --out /tmp/qd_ho_1116 > $S/gen_v1.log 2>&1 || fail gen_v1
cmp -s <(python3 -c "import json;print(json.dumps(json.load(open('/tmp/qd_ho_1116/labels.json')),sort_keys=True))") \
       <(python3 -c "import json;print(json.dumps(json.load(open('runs/ho_1116/held_labels.json')),sort_keys=True))") || fail v1_labels_differ
$PY bench/rejudge_hang.py --pool tests/sealed_hang --ai runs/ho_1116/sealed_ai.jsonl --naive runs/ho_1116/sealed_naive.jsonl --out $S/v1_sealed_rejudge.jsonl > $S/rejudge.log 2>&1
$PY bench/rejudge_hang.py --pool /tmp/qd_ho_1116 --ai runs/ho_1116/held_ai.jsonl --naive runs/ho_1116/held_naive.jsonl --out $S/v1_held_rejudge.jsonl >> $S/rejudge.log 2>&1
{ echo "## v1 sealed 7 (recorded fixes re-judged)"; $PY bench/score_structure.py tests/sealed_hang/labels.json --rejudge $S/v1_sealed_rejudge.jsonl
  echo; echo "## v1 held-out 20 (recorded fixes re-judged)"; $PY bench/score_structure.py runs/ho_1116/held_labels.json --rejudge $S/v1_held_rejudge.jsonl
} > $S/score_v1.md 2>&1
echo A-done > $S/state.$PHASE
[ "$PHASE" = A ] && exit 0
fi

echo B-code > $S/state.$PHASE
python3 tests/gen_hang/gen2.py --pool heldout --out /tmp/qd_ho2 --hash-only > $S/gen_v2.log 2>&1 || fail gen_v2
want=$(python3 -c "import json;print(json.load(open('tests/gen_hang/sealed2.json'))['labels_sha256'])")
grep -q "$want" $S/gen_v2.log || fail v2_labels_hash
$PY - <<'EOF' || fail v2_tree_hash
import hashlib, json, os
root = "/tmp/qd_ho2"; h = hashlib.sha256()
for d, _, fs in sorted(os.walk(root)):
    if os.path.relpath(d, root).split(os.sep)[0] == "common":
        continue
    for f in sorted(fs):
        if f != "labels.json":
            p = os.path.join(d, f); h.update(os.path.relpath(p, root).encode()); h.update(open(p, "rb").read())
assert h.hexdigest() == json.load(open("tests/gen_hang/sealed2.json"))["scenario_tree_sha256"]
EOF
HELD=$(ls -d /tmp/qd_ho2/t*)
$PY -m qnx_doctor.cli hang --no-ai --scenario $HELD --out $S/v2_code.jsonl > $S/v2_code.log 2>&1

echo B-ai > $S/state.$PHASE
$PY -m qnx_doctor.cli hang --scenario $HELD --out $S/v2_ai.jsonl > $S/v2_ai.log 2>&1 &
A=$!
$PY bench/naive_hang.py --pool /tmp/qd_ho2 --code $S/v2_code.jsonl --out $S/v2_naive.jsonl > $S/v2_naive.log 2>&1 &
B=$!
wait $A $B
cp /tmp/qd_ho2/labels.json $S/v2_labels.json
{ echo "## v2 held-out 30 (first run)"; $PY bench/score_structure.py $S/v2_labels.json --fresh code=$S/v2_code.jsonl ai=$S/v2_ai.jsonl naive=$S/v2_naive.jsonl
} > $S/score_v2.md 2>&1
echo done > $S/state.$PHASE
