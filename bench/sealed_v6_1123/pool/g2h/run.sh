#!/bin/sh
/var/qd/g2h/cfgd g2hcfg g2hkeys > /tmp/d0g2hcfg.log 2>&1 &
/var/qd/g2h/app g2happ g2hcfg > /tmp/d0g2happ.log 2>&1 &
sleep 4
