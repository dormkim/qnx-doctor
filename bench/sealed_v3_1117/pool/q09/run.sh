#!/bin/sh
rm -f /tmp/eeprom.id /tmp/eeprom.new
/var/qd/q09/eeprom > /tmp/q_eeprom.err 2>&1 &
/var/qd/q09/cfgrouter > /tmp/q_cfgrouter.err 2>&1 &
/var/qd/q09/hmi > /tmp/d0hmi.log 2>&1 &
/var/qd/q09/logpack 800 18 2 > /tmp/q_logpack.err 2>&1 &
sleep 4
