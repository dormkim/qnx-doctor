#!/bin/sh
/var/qd/E04/lowsrv d0e04b 15 > /tmp/d0e04b.log 2>&1 &
/var/qd/E04/hog d0e04c 20 > /tmp/d0e04c.log 2>&1 &
/var/qd/E04/hog d0e04d 22 > /tmp/d0e04d.log 2>&1 &
/var/qd/E04/hicli d0e04a d0e04b 30 120 > /tmp/d0e04a.log 2>&1 &
sleep 4
