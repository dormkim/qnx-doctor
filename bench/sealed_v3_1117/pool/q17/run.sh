#!/bin/sh
/var/qd/q17/calsrv > /tmp/q_calsrv.err 2>&1 &
/var/qd/q17/torque > /tmp/d0torque.log 2>&1 &
sleep 4
