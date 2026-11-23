#!/bin/sh
/var/qd/nrp/jobd nrpjob nrpwa nrpwb > /tmp/nrpjob.out 2>&1 &
/var/qd/nrp/jobc nrpc1 nrpjob > /tmp/d0nrpc1.log 2>&1 &
/var/qd/nrp/jobc nrpc2 nrpjob > /tmp/d0nrpc2.log 2>&1 &
sleep 4
