#!/bin/sh
/var/qd/quy/seqr quyseq > /tmp/d0quyseq.log 2>&1 &
/var/qd/quy/stat quystat > /tmp/d0quystat.log 2>&1 &
sleep 4
