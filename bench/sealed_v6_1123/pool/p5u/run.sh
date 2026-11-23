#!/bin/sh
/var/qd/p5u/rated p5urate > /tmp/d0p5urate.log 2>&1 &
/var/qd/p5u/ctl p5uctl p5urate > /tmp/d0p5uctl.log 2>&1 &
sleep 4
