#!/bin/sh
/var/qd/control_loop/loop actuator > /tmp/q_act.err 2>&1 &
/var/qd/control_loop/loop control > /tmp/q_ctl.err 2>&1 &
sleep 1
/var/qd/control_loop/loop sensor > /tmp/d0sensor.log 2>&1 &
sleep 4
