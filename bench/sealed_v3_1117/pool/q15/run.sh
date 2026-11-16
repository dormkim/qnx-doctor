#!/bin/sh
/var/qd/q15/svc ledger stock > /tmp/q_ledger.err 2>&1 &
/var/qd/q15/svc stock ledger > /tmp/q_stock.err 2>&1 &
/var/qd/q15/client till ledger > /tmp/d0till.log 2>&1 &
/var/qd/q15/client picker stock > /tmp/d0picker.log 2>&1 &
sleep 4
