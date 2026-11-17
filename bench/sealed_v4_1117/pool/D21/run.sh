#!/bin/sh
/var/qd/D21/pool_worker d021b > /tmp/d021b.log 2>&1 &
/var/qd/D21/pool_worker d021c > /tmp/d021c.log 2>&1 &
/var/qd/D21/pool_disp d021a d021b d021c > /tmp/d021a.log 2>&1 &
sleep 4
