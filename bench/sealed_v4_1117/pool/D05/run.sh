#!/bin/sh
/var/qd/D05/halfreply_srv d005b > /tmp/d005b.log 2>&1 &
/var/qd/D05/sender d005a d005b 150 > /tmp/d005a.log 2>&1 &
sleep 4
