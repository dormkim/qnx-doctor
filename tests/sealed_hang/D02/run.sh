#!/bin/sh
/var/qd/D02/stage d02a d02b > /tmp/d02a.log 2>&1 &
/var/qd/D02/stage d02b d02c > /tmp/d02b.log 2>&1 &
/var/qd/D02/stage d02c d02a > /tmp/d02c.log 2>&1 &
sleep 4
