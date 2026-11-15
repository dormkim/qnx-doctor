#!/bin/sh
/var/qd/D03/svc logger > /tmp/d03log.log 2>&1 &
/var/qd/D03/svc server > /tmp/d03srv.log 2>&1 &
sleep 1
/var/qd/D03/svc client > /tmp/d03cli.log 2>&1 &
sleep 4
