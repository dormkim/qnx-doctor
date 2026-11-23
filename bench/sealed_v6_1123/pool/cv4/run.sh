#!/bin/sh
/var/qd/cv4/catalogd cv4cat cv4ui cv4wa cv4wb > /tmp/cv4cat.out 2>&1 &
/var/qd/cv4/ui cv4ui cv4cat cv4r1 cv4r2 cv4ev > /tmp/cv4ui.out 2>&1 &
sleep 4
