#!/bin/sh
/var/qd/D16/reentr_s2 d016c d016b > /tmp/d016c.log 2>&1 &
/var/qd/D16/reentr_s1 d016b d016c > /tmp/d016b.log 2>&1 &
/var/qd/D16/sender d016a d016b 150 > /tmp/d016a.log 2>&1 &
sleep 4
