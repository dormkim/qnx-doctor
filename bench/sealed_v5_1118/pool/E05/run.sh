#!/bin/sh
/var/qd/E05/ring d0e05a d0e05b > /tmp/d0e05a.log 2>&1 &
/var/qd/E05/ring d0e05b d0e05a > /tmp/d0e05b.log 2>&1 &
sleep 4
