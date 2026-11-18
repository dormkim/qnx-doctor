#!/bin/sh
/var/qd/E10/nsrv d0e10a 15 > /tmp/d0e10a.log 2>&1 &
/var/qd/E10/load d0e10c 5 > /tmp/d0e10c.log 2>&1 &
/var/qd/E10/ncli d0e10b d0e10a 25 150 > /tmp/d0e10b.log 2>&1 &
sleep 4
