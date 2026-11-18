#!/bin/sh
/var/qd/E02/lowsrv d0e02b 3 > /tmp/d0e02b.log 2>&1 &
/var/qd/E02/hog d0e02c 20 > /tmp/d0e02c.log 2>&1 &
/var/qd/E02/hicli d0e02a d0e02b 40 120 > /tmp/d0e02a.log 2>&1 &
sleep 4
