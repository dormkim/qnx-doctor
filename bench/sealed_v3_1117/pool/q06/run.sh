#!/bin/sh
/var/qd/q06/codecd > /tmp/q_codecd.err 2>&1 &
/var/qd/q06/player > /tmp/d0player.log 2>&1 &
/var/qd/q06/indexer 800 18 2 > /tmp/q_indexer.err 2>&1 &
sleep 4
