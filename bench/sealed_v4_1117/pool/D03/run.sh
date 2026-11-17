#!/bin/sh
/var/qd/D03/ring d003a d003b 0 > /tmp/d003a.log 2>&1 &
/var/qd/D03/ring d003b d003c 0 > /tmp/d003b.log 2>&1 &
/var/qd/D03/ring d003c d003a 1 > /tmp/d003c.log 2>&1 &
sleep 4
