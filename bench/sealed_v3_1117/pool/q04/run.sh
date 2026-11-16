#!/bin/sh
/var/qd/q04/initdb > /tmp/q_initdb.err 2>&1
/var/qd/q04/admind > /tmp/q_admind.err 2>&1 &
/var/qd/q04/fltr > /tmp/q_fltr.err 2>&1 &
/var/qd/q04/sampler > /tmp/d0sampler.log 2>&1 &
sleep 4
