#!/bin/sh
rm -f /tmp/planner.id /tmp/planner.new
/var/qd/q21/planner > /tmp/q_planner.err 2>&1 &
/var/qd/q21/auditd > /tmp/q_auditd.err 2>&1 &
/var/qd/q21/pilot > /tmp/d0pilot.log 2>&1 &
/var/qd/q21/mapper 600 18 2 > /tmp/q_mapper.err 2>&1 &
sleep 4
