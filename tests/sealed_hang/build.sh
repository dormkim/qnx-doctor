#!/bin/sh
# build.sh <out-dir>: cross-compile every scenario for x86_64 QNX with qcc (SDP environment must be sourced).
set -e
out=$1; here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out"
qcc -Vgcc_ntox86_64 -o "$out/snap" "$here/common/snap.c"
qcc -Vgcc_ntox86_64 -o "$out/hi" "$here/common/hi.c"
cp "$here/common/check.sh" "$out/check.sh"
for d in D01 D02 D03 D04 D05 D06 D07; do
  mkdir -p "$out/$d"; cp "$here/$d/run.sh" "$out/$d/run.sh"
  for c in "$here/$d"/*.c; do b=$(basename "$c" .c); qcc -Vgcc_ntox86_64 -o "$out/$d/$b" "$c" -lc; done
done
echo built "$out"
