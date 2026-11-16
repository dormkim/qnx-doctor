#!/bin/sh
/var/qd/q12/busgate > /tmp/q_busgate.err 2>&1 &
/var/qd/q12/ecu > /tmp/d0ecu.log 2>&1 &
sleep 4
