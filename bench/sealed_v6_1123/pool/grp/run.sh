#!/bin/sh
/var/qd/grp/imud grpimu > /tmp/d0grpimu.log 2>&1 &
/var/qd/grp/fc grpfc grpimu > /tmp/d0grpfc.log 2>&1 &
/var/qd/grp/logfmt grplog > /tmp/d0grplog.log 2>&1 &
sleep 4
