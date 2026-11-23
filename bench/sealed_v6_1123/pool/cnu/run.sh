#!/bin/sh
/var/qd/cnu/stage cnuacq cnuscl > /tmp/d0cnuacq.log 2>&1 &
/var/qd/cnu/stage cnuscl cnuenc > /tmp/d0cnuscl.log 2>&1 &
/var/qd/cnu/stage cnuenc cnuacq > /tmp/d0cnuenc.log 2>&1 &
sleep 4
