#!/bin/sh
# check.sh <Dxx>: start the observer, then the scenario; when run.sh returns, the observer prints a pidin snapshot
# (priority 63) and each role's TICK count at that moment. The observer is loaded and started first, and is woken
# with the builtin `kill`, because /var and /tmp are on the disk and a hog above the disk driver's priority would
# stall loading it (see snap.c; harness fix 2026-11-16, labels unchanged).
s=$1
rm -f /tmp/d0*.log
/var/qd/snap &
snap=$!
sh /var/qd/$s/run.sh
kill -USR1 $snap
wait $snap
echo QDDONE
