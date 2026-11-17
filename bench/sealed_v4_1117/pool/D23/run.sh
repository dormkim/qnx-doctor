#!/bin/sh
/var/qd/D23/lowfix_srv d023b > /tmp/d023b.log 2>&1 &
/var/qd/D23/hog d023c > /tmp/d023c.log 2>&1 &
/var/qd/D23/pp_client d023a d023b > /tmp/d023a.log 2>&1 &
sleep 4
