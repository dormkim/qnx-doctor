#!/bin/sh
/var/qd/qsa/sensd qsasen > /tmp/d0qsasen.log 2>&1 &
/var/qd/qsa/hmi qsahmi qsasen > /tmp/d0qsahmi.log 2>&1 &
/var/qd/qsa/crunch qsacr > /tmp/d0qsacr.log 2>&1 &
sleep 4
