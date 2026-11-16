#!/bin/sh
/var/qd/q01/telemetryd > /tmp/q_telemetryd.err 2>&1 &
/var/qd/q01/probe > /tmp/d0probe.log 2>&1 &
sleep 4
