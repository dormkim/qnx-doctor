#!/bin/sh
rm -f /tmp/ctrlsrv.id /tmp/ctrlsrv.new
/var/qd/q02/ctrlsrv --rt > /tmp/q_ctrlsrv.err 2>&1 &
/var/qd/q02/ctlloop > /tmp/d0ctlloop.log 2>&1 &
/var/qd/q02/encoder 800 18 2 > /tmp/q_encoder.err 2>&1 &
sleep 4
