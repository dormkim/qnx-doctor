#!/bin/sh
/var/qd/q03/cfgd > /tmp/q_cfgd.err 2>&1 &
/var/qd/q03/appcfg > /tmp/d0appcfg.log 2>&1 &
sleep 4
