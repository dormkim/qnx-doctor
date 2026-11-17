#!/bin/sh
/var/qd/D19/twomsg_srv d019b > /tmp/d019b.log 2>&1 &
/var/qd/D19/timed_client d019a d019b > /tmp/d019a.log 2>&1 &
sleep 4
