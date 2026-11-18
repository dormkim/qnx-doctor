#!/bin/sh
/var/qd/E06/ring d0e06a d0e06b > /tmp/d0e06a.log 2>&1 &
/var/qd/E06/ring d0e06b d0e06c > /tmp/d0e06b.log 2>&1 &
/var/qd/E06/ring d0e06c d0e06a > /tmp/d0e06c.log 2>&1 &
sleep 4
