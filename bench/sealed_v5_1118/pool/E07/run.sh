#!/bin/sh
/var/qd/E07/halfsrv d0e07b > /tmp/d0e07b.log 2>&1 &
/var/qd/E07/sender d0e07a d0e07b 150 > /tmp/d0e07a.log 2>&1 &
sleep 4
