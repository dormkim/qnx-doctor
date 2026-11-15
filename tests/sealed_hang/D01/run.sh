#!/bin/sh
/var/qd/D01/pingpong d01a d01b > /tmp/d01a.log 2>&1 &
/var/qd/D01/pingpong d01b d01a > /tmp/d01b.log 2>&1 &
sleep 4
