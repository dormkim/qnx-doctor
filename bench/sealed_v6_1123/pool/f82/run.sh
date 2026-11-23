#!/bin/sh
/var/qd/f82/eeprom f82eep > /tmp/d0f82eep.log 2>&1 &
/var/qd/f82/bus f82bus f82eep > /tmp/d0f82bus.log 2>&1 &
/var/qd/f82/pilot f82plt f82bus > /tmp/d0f82plt.log 2>&1 &
/var/qd/f82/scrub f82scr > /tmp/d0f82scr.log 2>&1 &
sleep 4
