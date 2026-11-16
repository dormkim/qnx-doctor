#!/bin/sh
/var/qd/q07/slotd > /tmp/q_slotd.err 2>&1 &
/var/qd/q07/radio > /tmp/d0radio.log 2>&1 &
sleep 4
