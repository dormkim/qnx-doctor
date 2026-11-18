/* qd_start: every scenario program starts at the normal QNX priority (10), linked in by the harness (hang.py build)
 * like qd_trace.c. The scenario source is unchanged; roles that set a priority themselves (setprio in a server,
 * client or CPU load) still do so after this runs.
 *
 * Why (harness fix, 2026-11-17): check.sh runs under `hi` at priority 50 so that a scenario's CPU load cannot delay
 * the shell's own sleep and the observer's wake-up. Programs started from run.sh inherited that 50. A ring fixed with
 * a pulse can then loop without blocking at 50, above the serial driver (25) and the disk driver (21) that the
 * observer needs, and once (v1 s7628ec) the snapshot came back incomplete. At 10 the programs stay below the drivers,
 * the shell and the observer. Labels are unchanged: every priority a label depends on (server 3-8, client 25-40,
 * load 1-22) is set by the program itself. */
#include <pthread.h>

__attribute__((constructor)) static void qd_start_normal_priority(void) { pthread_setschedprio(pthread_self(), 10); }
