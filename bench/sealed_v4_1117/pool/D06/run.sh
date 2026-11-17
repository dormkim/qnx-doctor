#!/bin/sh
/var/qd/D06/idle_srv d006a > /tmp/d006a.log 2>&1 &
/var/qd/D06/sender d006b d006a 400 > /tmp/d006b.log 2>&1 &
sleep 4
