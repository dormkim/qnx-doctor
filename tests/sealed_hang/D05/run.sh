#!/bin/sh
rm -f /tmp/d05srv.id
/var/qd/D05/prio server > /tmp/d05srv.log 2>&1 &
/var/qd/D05/prio client > /tmp/d05ctl.log 2>&1 &
sleep 1
: > /tmp/d05ctl.log
/var/qd/D05/prio hog 20 > /dev/null 2>&1 &
sleep 4
