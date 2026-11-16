#!/usr/bin/env bash
# The next sealed set (planned 11/19-21: hand-written by a fresh agent that has not seen the code), run ONCE with four
# arms. The «naive_x2» arm is new (red team 2026-11-16): the one-shot baseline given the same two tries as ours, told
# only what the rerun showed in a developer's terms (TICK counts, verifier text), never the wait graph. So
# «ours vs naive_x2» isolates what the pidin graph, docs and probes add; «first try fixed» isolates the retry loop.
# The existing held-out sets (v1 20, v2 30) are NOT run again here.
#
#   bench/run_sealed3.sh POOL_DIR LABELS.json OUT_DIR      (server only, detached; QEMU runs one at a time via the lock)
# Writes OUT_DIR/state (code / fix / done / fail:<why>) and OUT_DIR/score.md. States only (QNX licence 4.6(i)).
set -u
POOL=$1; LABELS=$2; S=$3
set -a; . ~/.config/qnx-doctor/env; set +a
cd ~/personal/qnx-doctor
mkdir -p "$S"; PY=.venv/bin/python
fail() { echo "fail:$1" > "$S/state"; exit 1; }
[ -s "$S/code.jsonl" ] && fail "out dir already used: a sealed set is run once"
case "$LABELS" in "$POOL"/*) fail "labels inside the pool: the AI could read them";; esac
SCEN=$(ls -d "$POOL"/*/ | grep -v '/common/$')
echo code > "$S/state"
$PY -m qnx_doctor.cli hang --no-ai --scenario $SCEN --out "$S/code.jsonl" > "$S/code.log" 2>&1 || fail code
echo fix > "$S/state"
$PY -m qnx_doctor.cli hang --scenario $SCEN --out "$S/ai.jsonl" > "$S/ai.log" 2>&1 & A=$!
$PY bench/naive_hang.py --pool "$POOL" --code "$S/code.jsonl" --out "$S/naive.jsonl" > "$S/naive.log" 2>&1 & B=$!
$PY bench/naive_hang.py --pool "$POOL" --code "$S/code.jsonl" --out "$S/naive_x2.jsonl" --attempts 2 > "$S/naive_x2.log" 2>&1 & C=$!
wait $A $B $C
cp "$LABELS" "$S/labels.json"
EXC=$(dirname "$POOL")/excluded.json   # reproducibility check before the run (README rule 2); absent = none excluded
[ -f "$EXC" ] && cp "$EXC" "$S/excluded.json" && XARG="--exclude-file $S/excluded.json" || XARG=""
$PY bench/score_structure.py "$S/labels.json" $XARG --fresh code="$S/code.jsonl" ai="$S/ai.jsonl" naive="$S/naive.jsonl" naive_x2="$S/naive_x2.jsonl" > "$S/score.md" 2>&1
echo done > "$S/state"
