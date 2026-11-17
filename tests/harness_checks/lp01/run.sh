#!/bin/sh
/var/qd/lp01/late > /tmp/q_late.err 2>&1 &
/var/qd/lp01/asker > /tmp/d0asker.log 2>&1 &
sleep 3
