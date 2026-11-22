#!/usr/bin/env bash
# A sealed set, run ONCE with four arms (code / ours / naive / naive_x2, same model). Written for v3; since 2026-11-22
# it runs the v6 plan (bench/V6_PLAN.md): one core (QD_SMP=1) and both baselines may answer «unknown». The sets up to
# v5 are not run again; the script they used is this file at commit 8ac11ad.
# «naive_x2» = the baseline with the same two tries as ours, told only what the rerun showed in a developer's terms,
# never the wait graph.
#
#   bench/run_sealed3.sh POOL_DIR LABELS.json OUT_DIR      (server only, detached; QEMU runs one at a time via the lock)
#
# The key comes from ~/.config/qnx-doctor/env and from nowhere else: the caller's ANTHROPIC_* and QD_MODEL are
# dropped, and an empty ANTHROPIC_API_KEY stops the run before any boot. It runs the checkout it lives in (run it
# from the freeze commit); QD_PYTHON names the interpreter if that checkout has no .venv.
# Writes OUT_DIR/state (code / fix / score / done / fail:<why>), OUT_DIR/commit and OUT_DIR/score.md. «done» only if
# every arm ended well with a row for every scenario. States only (QNX licence 4.6(i)).
set -u
[ $# -eq 3 ] || { echo "usage: $0 POOL_DIR LABELS.json OUT_DIR" >&2; exit 2; }
POOL=$(readlink -f "$1"); LABELS=$(readlink -f "$2"); S=$(readlink -f "$3")
REPO=$(dirname "$(dirname "$(readlink -f "$0")")")
if [ -e "$S" ] && [ -n "$(ls -A "$S")" ]; then
  echo "out dir already used: a sealed set is run once" >&2; exit 1
fi
mkdir -p "$S"
fail() { echo "fail:$1" > "$S/state"; echo "fail:$1" >&2; exit 1; }
[ -d "$POOL" ] && [ -f "$LABELS" ] || fail "no pool or no labels"
case "$LABELS" in "$POOL"/*) fail "labels inside the pool: the AI could read them";; esac

for v in ${!ANTHROPIC_@}; do unset "$v"; done
ENV_FILE=$HOME/.config/qnx-doctor/env
[ -r "$ENV_FILE" ] || fail "no env file"
set -a; . "$ENV_FILE" || fail "env file"; set +a
[ -n "${ANTHROPIC_API_KEY:-}" ] || fail "ANTHROPIC_API_KEY is empty"
export QD_SMP=1 QD_MODEL=claude-opus-5-5

cd "$REPO" || fail "no checkout"
PY=${QD_PYTHON:-$REPO/.venv/bin/python}
[ -x "$PY" ] || fail "no python (set QD_PYTHON)"
git rev-parse HEAD > "$S/commit" 2>/dev/null

SCEN=()
for d in "$POOL"/*/; do [ "$(basename "$d")" = common ] || SCEN+=("$d"); done
N=${#SCEN[@]}
[ "$N" -gt 0 ] && [ -d "${SCEN[0]}" ] || fail "empty pool"
rows() { if [ -f "$1" ]; then wc -l < "$1"; else echo 0; fi; }

echo code > "$S/state"
"$PY" -m qnx_doctor.cli hang --no-ai --scenario "${SCEN[@]}" --out "$S/code.jsonl" > "$S/code.log" 2>&1 || fail code
[ "$(rows "$S/code.jsonl")" -eq "$N" ] || fail "code: rows missing"
SEEN=$(grep -c '"kind": "graph"' "$S/code.jsonl")   # the baselines get only what the code run could observe

echo fix > "$S/state"
"$PY" -m qnx_doctor.cli hang --scenario "${SCEN[@]}" --out "$S/ai.jsonl" > "$S/ai.log" 2>&1 & A=$!
"$PY" bench/naive_hang.py --allow-unknown --pool "$POOL" --code "$S/code.jsonl" --out "$S/naive.jsonl" > "$S/naive.log" 2>&1 & B=$!
"$PY" bench/naive_hang.py --allow-unknown --pool "$POOL" --code "$S/code.jsonl" --out "$S/naive_x2.jsonl" --attempts 2 > "$S/naive_x2.log" 2>&1 & C=$!
BAD=""
wait "$A" || BAD="$BAD ai"
wait "$B" || BAD="$BAD naive"
wait "$C" || BAD="$BAD naive_x2"
[ -z "$BAD" ] || fail "fix:$BAD"
[ "$(rows "$S/ai.jsonl")" -eq "$N" ] || fail "ai: rows missing"
for a in naive naive_x2; do [ "$(rows "$S/$a.jsonl")" -eq "$SEEN" ] || fail "$a: rows missing"; done

echo score > "$S/state"
cp "$LABELS" "$S/labels.json" || fail labels
XARG=()
EXC=$(dirname "$POOL")/excluded.json   # reproducibility check before the run; absent = none excluded
if [ -f "$EXC" ]; then
  cp "$EXC" "$S/excluded.json" || fail excluded
  XARG=(--exclude-file "$S/excluded.json")
fi
"$PY" bench/score_structure.py "$S/labels.json" ${XARG[@]+"${XARG[@]}"} --fresh code="$S/code.jsonl" ai="$S/ai.jsonl" naive="$S/naive.jsonl" naive_x2="$S/naive_x2.jsonl" > "$S/score.md" 2>&1 || fail score
echo done > "$S/state"
