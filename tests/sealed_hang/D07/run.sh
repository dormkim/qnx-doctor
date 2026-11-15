#!/bin/sh
/var/qd/D07/idle d07w1 > /tmp/d07w1.log 2>&1 &
/var/qd/D07/idle d07w2 > /tmp/d07w2.log 2>&1 &
sleep 1
/var/qd/D07/idle feeder > /tmp/d07feed.log 2>&1 &
sleep 4
