#!/bin/sh
/var/qd/q08/relay ingest parse 1 > /tmp/d0ingest.log 2>&1 &
/var/qd/q08/relay parse archive 0 > /tmp/d0parse.log 2>&1 &
/var/qd/q08/relay archive ingest 0 > /tmp/d0archive.log 2>&1 &
sleep 4
