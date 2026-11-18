#!/bin/sh
/var/qd/E09/nsrv d0e09a 15 > /tmp/d0e09a.log 2>&1 &
/var/qd/E09/ncli d0e09b d0e09a 15 150 > /tmp/d0e09b.log 2>&1 &
sleep 4
