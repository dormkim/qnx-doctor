#!/bin/sh
/var/qd/kp6/kvstore kp6kv > /tmp/d0kp6kv.log 2>&1 &
/var/qd/kp6/kvclient kp6wr kp6kv w > /tmp/d0kp6wr.log 2>&1 &
/var/qd/kp6/kvclient kp6rd kp6kv r > /tmp/d0kp6rd.log 2>&1 &
sleep 4
