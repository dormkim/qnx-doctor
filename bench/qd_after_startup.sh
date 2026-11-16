#!/bin/sh
# Transport for the QEMU demo of `hang --live`: boot the image, wait until the image's own startup script has
# finished (its post_start snippet has then started the program, as on a deployed system), then run the line.
#   bench/qd_after_startup.sh IMAGE_DIR "shell line"
# It waits for the system, not for our program. On a board the transport is simply `ssh root@<target>`.
QD_EXEC_TIMEOUT=${QD_EXEC_TIMEOUT:-200} exec "$(dirname "$0")/../bin/qd-target-exec" "$1" \
  "n=0; while pidin arg | grep -q "[/]proc/boot/startup.sh" && [ \$n -lt 150 ]; do sleep 1; n=\$((n+1)); done; sleep 2; $2"
