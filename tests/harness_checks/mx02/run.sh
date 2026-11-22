#!/bin/sh
/var/qd/mx02/desk > /tmp/q_desk.err 2>&1 &
/var/qd/mx02/teller > /tmp/d0teller.log 2>&1 &
sleep 4
