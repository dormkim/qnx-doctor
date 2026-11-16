#!/bin/sh
/var/qd/q11/parsed > /tmp/q_parsed.err 2>&1 &
/var/qd/q11/uplink > /tmp/d0uplink.log 2>&1 &
sleep 4
