#!/bin/sh
/var/qd/k74/audiod k74aud > /tmp/d0k74aud.log 2>&1 &
/var/qd/k74/player k74ply k74aud > /tmp/d0k74ply.log 2>&1 &
sleep 4
