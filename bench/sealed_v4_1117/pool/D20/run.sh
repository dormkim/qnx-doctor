#!/bin/sh
/var/qd/D20/lowfix_srv d020b > /tmp/d020b.log 2>&1 &
/var/qd/D20/hog d020c > /tmp/d020c.log 2>&1 &
/var/qd/D20/hiclient d020a d020b > /tmp/d020a.log 2>&1 &
/var/qd/D20/spin_flag d020d > /tmp/d020d.log 2>&1 &
sleep 4
