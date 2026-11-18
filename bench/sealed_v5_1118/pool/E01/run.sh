#!/bin/sh
/var/qd/E01/lowsrv d0e01b 12 > /tmp/d0e01b.log 2>&1 &
/var/qd/E01/hog d0e01c 20 > /tmp/d0e01c.log 2>&1 &
/var/qd/E01/hicli d0e01a d0e01b 30 120 > /tmp/d0e01a.log 2>&1 &
sleep 4
