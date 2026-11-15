#!/bin/sh
# check.sh <Dxx>: start the scenario, wait, then print a pidin snapshot (taken at top priority) and each role's TICK count.
s=$1
rm -f /tmp/d0*.log
sh /var/qd/$s/run.sh
echo "=== PIDIN ==="
/var/qd/snap
echo "=== TICKS ==="
for f in /tmp/d0*.log; do echo "$f $(grep -c TICK $f)"; done
echo QDDONE
