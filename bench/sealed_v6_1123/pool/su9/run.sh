#!/bin/sh
/var/qd/su9/evq su9evq > /tmp/d0su9evq.log 2>&1 &
/var/qd/su9/mon su9mon su9evq > /tmp/d0su9mon.log 2>&1 &
sleep 4
