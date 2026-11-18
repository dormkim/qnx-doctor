#!/bin/sh
/var/qd/E08/stopsrv d0e08b > /tmp/d0e08b.log 2>&1 &
/var/qd/E08/sender d0e08a d0e08b 120 > /tmp/d0e08a.log 2>&1 &
sleep 4
