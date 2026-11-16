#!/bin/sh
/var/qd/q19/evbus > /tmp/q_evbus.err 2>&1 &
/var/qd/q19/dash > /tmp/d0dash.log 2>&1 &
sleep 4
