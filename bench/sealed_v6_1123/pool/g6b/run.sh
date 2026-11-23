#!/bin/sh
/var/qd/g6b/pwrmgr g6bpwr > /tmp/d0g6bpwr.log 2>&1 &
/var/qd/g6b/hmi g6bhmi g6bpwr > /tmp/d0g6bhmi.log 2>&1 &
sleep 4
