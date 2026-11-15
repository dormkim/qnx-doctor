#!/bin/sh
/var/qd/D06/slow server > /tmp/d06srv.log 2>&1 &
sleep 1
/var/qd/D06/slow client > /tmp/d06cli.log 2>&1 &
sleep 4
