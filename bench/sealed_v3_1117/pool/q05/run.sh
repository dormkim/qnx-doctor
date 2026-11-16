#!/bin/sh
/var/qd/q05/flashd > /tmp/q_flashd.err 2>&1 &
/var/qd/q05/datalog > /tmp/d0datalog.log 2>&1 &
sleep 4
