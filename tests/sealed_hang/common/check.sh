#!/bin/sh
# check.sh <Dxx>: start the observer, then the scenario; when run.sh returns, the observer prints a pidin snapshot
# (priority 63) and each role's TICK count at that moment. The observer is loaded and started first, and is woken
# with the builtin `kill`, because /var and /tmp are on the disk and a hog above the disk driver's priority would
# stall loading it (see snap.c; harness fix 2026-11-16, labels unchanged).
s=$1
# /tmp in RAM (harness fix 2026-11-17, before sealed v4; docs/분석_sealed3_1117.md §4): a procnto link over the disk
# directory, so TICK logs, *.id files and the observer's reads of them never wait for the disk driver (devb-eide,
# priority 21) under a CPU load above 21: a loop blocks on its message peer, not on writing its log. The second TICK
# count that the reproducibility check needs now comes from this same observer (snap.c TICKS2), not from a second
# observer woken after check.sh, which hung under such a load (v3: four priority-chain scenarios excluded; harness
# check oc01). The image is fresh on every boot, so nothing has to be undone.
ln -sP /dev/shmem /tmp
rm -f /tmp/d0*.log /dev/shmem/qdm.*
/var/qd/snap &
snap=$!
sh /var/qd/$s/run.sh
kill -USR1 $snap
wait $snap
echo QDDONE
