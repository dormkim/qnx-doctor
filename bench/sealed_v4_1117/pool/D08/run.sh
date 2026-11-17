#!/bin/sh
/var/qd/D08/lowfix_srv d008b > /tmp/d008b.log 2>&1 &
/var/qd/D08/hog d008c > /tmp/d008c.log 2>&1 &
/var/qd/D08/hiclient d008a d008b > /tmp/d008a.log 2>&1 &
sleep 4
