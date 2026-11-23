#!/bin/sh
/var/qd/bkr/dbd bkrdb bkrhmi > /tmp/d0bkrdb.log 2>&1 &
/var/qd/bkr/gw bkrgw bkrdb > /tmp/d0bkrgw.log 2>&1 &
/var/qd/bkr/hmi bkrhmi bkrgw > /tmp/d0bkrhmi.log 2>&1 &
sleep 4
