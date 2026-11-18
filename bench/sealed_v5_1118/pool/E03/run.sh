#!/bin/sh
/var/qd/E03/lowsrv d0e03c 10 > /tmp/d0e03c.log 2>&1 &
/var/qd/E03/hog d0e03d 20 > /tmp/d0e03d.log 2>&1 &
/var/qd/E03/hicli d0e03a d0e03c 28 120 > /tmp/d0e03a.log 2>&1 &
/var/qd/E03/hicli d0e03b d0e03c 32 140 > /tmp/d0e03b.log 2>&1 &
sleep 4
