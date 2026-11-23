#!/bin/sh
/var/qd/qgj/adcd qgjadc > /tmp/d0qgjadc.log 2>&1 &
/var/qd/qgj/ctl qgjctl qgjadc > /tmp/d0qgjctl.log 2>&1 &
/var/qd/qgj/bgcrc qgjcrc > /tmp/d0qgjcrc.log 2>&1 &
sleep 4
