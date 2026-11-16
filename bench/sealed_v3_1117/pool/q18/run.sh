#!/bin/sh
rm -f /tmp/imu.id /tmp/imu.new
/var/qd/q18/imu > /tmp/q_imu.err 2>&1 &
/var/qd/q18/gimbal > /tmp/d0gimbal.log 2>&1 &
/var/qd/q18/vidproc 500 18 2 15 35 > /tmp/q_vidproc.err 2>&1 &
sleep 4
