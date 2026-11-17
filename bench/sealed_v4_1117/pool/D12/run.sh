#!/bin/sh
/var/qd/D12/offbyone_srv d012b > /tmp/d012b.log 2>&1 &
/var/qd/D12/sender d012a d012b 150 > /tmp/d012a.log 2>&1 &
sleep 4
