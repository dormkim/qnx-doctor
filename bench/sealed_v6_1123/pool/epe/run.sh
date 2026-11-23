#!/bin/sh
/var/qd/epe/auth epeauth epekeys > /tmp/d0epeauth.log 2>&1 &
/var/qd/epe/broker epebrk epeauth > /tmp/d0epebrk.log 2>&1 &
/var/qd/epe/keys epekeys epebrk > /tmp/d0epekeys.log 2>&1 &
/var/qd/epe/ui epeui epebrk > /tmp/d0epeui.log 2>&1 &
sleep 4
