#!/bin/sh
/var/qd/euf/gpsd eufgps > /tmp/d0eufgps.log 2>&1 &
/var/qd/euf/nav eufnav eufgps > /tmp/d0eufnav.log 2>&1 &
/var/qd/euf/mapgen eufmap > /tmp/d0eufmap.log 2>&1 &
sleep 4
