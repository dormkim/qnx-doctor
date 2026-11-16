#!/bin/sh
/var/qd/q13/valve > /tmp/q_valve.err 2>&1 &
/var/qd/q13/alarmd > /tmp/q_alarmd.err 2>&1 &
/var/qd/q13/pumpctl > /tmp/d0pumpctl.log 2>&1 &
/var/qd/q13/panel > /tmp/d0panel.log 2>&1 &
sleep 4
