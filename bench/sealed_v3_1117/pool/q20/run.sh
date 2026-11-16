#!/bin/sh
/var/qd/q20/framestore > /tmp/q_fs.err 2>&1 &
/var/qd/q20/journal > /tmp/q_journal.err 2>&1 &
/var/qd/q20/cam > /tmp/d0cam.log 2>&1 &
sleep 4
