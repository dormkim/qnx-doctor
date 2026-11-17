#!/bin/sh
/var/qd/sp01/store > /tmp/q_store.err 2>&1 &
/var/qd/sp01/meter > /tmp/d0meter.log 2>&1 &
sleep 3
