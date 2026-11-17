#!/bin/sh
/var/qd/D01/relay_srv d001a > /tmp/d001a.log 2>&1 &
/var/qd/D01/relay_cli d001b d001a > /tmp/d001b.log 2>&1 &
sleep 4
