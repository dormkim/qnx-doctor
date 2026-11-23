#!/bin/sh
/var/qd/exw/batchd exwbat exwfl > /tmp/d0exwbat.log 2>&1 &
/var/qd/exw/logger exwlog exwbat > /tmp/d0exwlog.log 2>&1 &
sleep 4
