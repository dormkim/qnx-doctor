#!/bin/sh
/var/qd/pump_ctl/pump pcpump > /tmp/d0pcpump.log 2>&1 &
/var/qd/pump_ctl/ctl pcctl pcpump > /tmp/d0pcctl.log 2>&1 &
sleep 4
