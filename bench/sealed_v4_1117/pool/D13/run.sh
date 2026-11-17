#!/bin/sh
/var/qd/D13/pool_worker d013d > /tmp/d013d.log 2>&1 &
/var/qd/D13/chain_s2 d013c d013d > /tmp/d013c.log 2>&1 &
/var/qd/D13/chain_s1 d013b d013c > /tmp/d013b.log 2>&1 &
/var/qd/D13/hog d013e > /tmp/d013e.log 2>&1 &
/var/qd/D13/sender d013a d013b 150 > /tmp/d013a.log 2>&1 &
sleep 4
