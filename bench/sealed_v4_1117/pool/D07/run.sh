#!/bin/sh
/var/qd/D07/pair_send d007a d007b > /tmp/d007a.log 2>&1 &
/var/qd/D07/pair_send d007b d007a > /tmp/d007b.log 2>&1 &
/var/qd/D07/noreply_srv d007d > /tmp/d007d.log 2>&1 &
/var/qd/D07/sender d007c d007d 150 > /tmp/d007c.log 2>&1 &
sleep 4
