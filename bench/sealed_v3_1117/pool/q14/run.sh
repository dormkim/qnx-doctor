#!/bin/sh
/var/qd/q14/lockd > /tmp/q_lockd.err 2>&1 &
/var/qd/q14/cell welder > /tmp/d0welder.log 2>&1 &
/var/qd/q14/cell painter > /tmp/d0painter.log 2>&1 &
/var/qd/q14/cell sorter > /tmp/d0sorter.log 2>&1 &
sleep 4
