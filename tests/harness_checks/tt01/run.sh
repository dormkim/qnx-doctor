#!/bin/sh
rm -f /dev/shmem/ttmute.id
/var/qd/tt01/mute > /tmp/q_mute.err 2>&1 &
/var/qd/tt01/waiter > /tmp/d0waiter.log 2>&1 &
/var/qd/tt01/cli > /tmp/d0cli.log 2>&1 &
sleep 3
