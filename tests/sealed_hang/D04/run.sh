#!/bin/sh
/var/qd/D04/cb server > /tmp/d04srv.log 2>&1 &
sleep 1
/var/qd/D04/cb client > /tmp/d04cli.log 2>&1 &
sleep 4
