#!/bin/sh
/var/qd/q10/routemap > /tmp/q_routemap.err 2>&1 &
/var/qd/q10/navcore > /tmp/d0navcore.log 2>&1 &
sleep 4
