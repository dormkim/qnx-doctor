#!/bin/sh
/var/qd/q16/peer east west 300 > /tmp/d0east.log 2>&1 &
/var/qd/q16/peer west east 900 > /tmp/d0west.log 2>&1 &
sleep 4
