#!/bin/sh
/var/qd/zte/collector ztecola ztemrga > /tmp/d0ztecola.log 2>&1 &
/var/qd/zte/merger ztemrga ztecolb > /tmp/d0ztemrga.log 2>&1 &
/var/qd/zte/collector ztecolb ztemrgb > /tmp/d0ztecolb.log 2>&1 &
/var/qd/zte/merger ztemrgb ztecola > /tmp/d0ztemrgb.log 2>&1 &
sleep 4
