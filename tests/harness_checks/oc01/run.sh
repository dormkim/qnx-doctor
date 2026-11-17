#!/bin/sh
rm -f /tmp/ocslow.id
/var/qd/oc01/slow > /tmp/q_slow.err 2>&1 &
/var/qd/oc01/ctl > /tmp/d0ctl.log 2>&1 &
sleep 1
/var/qd/oc01/load > /tmp/q_load.err 2>&1 &
sleep 2
