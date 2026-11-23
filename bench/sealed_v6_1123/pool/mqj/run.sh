#!/bin/sh
/var/qd/mqj/lidar mqjlid > /tmp/d0mqjlid.log 2>&1 &
/var/qd/mqj/planner mqjpln mqjlid > /tmp/d0mqjpln.log 2>&1 &
sleep 4
