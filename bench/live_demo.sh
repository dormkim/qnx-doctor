#!/usr/bin/env bash
# One round of the «attach to a running target» path (2026-11-16, red team 1-a), on our demo program only.
# Nothing of the test harness is used: loop.c is built with plain qcc (no qd_trace.c / --wrap, no qd_start.c), the
# image starts the three processes itself at boot (mkqnximage post_start snippet, as a deployed system would), and
# there is no run.sh, check.sh, snap or TICK log. qnx-doctor only gets a shell line on the target through a
# transport (here bench/qd_after_startup.sh → bin/qd-target-exec: the QEMU guest has no network; on a board it would be `ssh root@<target>`).
#   bench/live_demo.sh [SCENARIO_DIR] [OUT.jsonl]     (server; QEMU one at a time via the lock)
set -eu
SCEN=${1:-scenarios/hang_demo/control_loop}
OUT=${2:-runs/live_1116.jsonl}
cd "$(dirname "$0")/.."
export QNX_SDP=${QNX_SDP:-$HOME/personal/qnx/qnx800} QD_QEMU_ROOT=${QD_QEMU_ROOT:-$HOME/personal/qemu_local/root}
W=$(mktemp -d /tmp/qd-live-XXXXXX)
trap 'rm -rf "$W"' EXIT
mkdir -p "$W/out" "$W/vm/local/snippets" "$(dirname "$OUT")"
(
  . "$QNX_SDP/qnxsdp-env.sh" > /dev/null
  qcc -Vgcc_ntox86_64 -o "$W/out/loop" "$SCEN/loop.c"
  echo "[perms=0755] /var/app/loop=$W/out/loop" > "$W/vm/local/snippets/data_files.custom"
  cat > "$W/vm/local/snippets/post_start.custom" <<'X'
/var/app/loop actuator > /dev/null 2>&1 &
/var/app/loop control > /dev/null 2>&1 &
sleep 1
/var/app/loop sensor > /dev/null 2>&1 &
X
  cd "$W/vm" && mkqnximage --type=qemu --arch=x86_64 --ssh-ident=none --noprompt --clean > "$W/mkimg.log" 2>&1 \
    || { tail -20 "$W/mkimg.log"; exit 1; }
)
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
$PY -m qnx_doctor.cli hang --live "$PWD/bench/qd_after_startup.sh $W/vm" --src "$SCEN" --out "$OUT"
