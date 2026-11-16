#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* busgate: gateway to the vehicle bus. Before the first request is served it waits for the platform
 * supervisor (sysmgr, started by the board start-up script) to signal SIGUSR2 once the bus is configured. */
int main(void) {
  sigset_t set; sigemptyset(&set); sigaddset(&set, SIGUSR2);
  pthread_sigmask(SIG_BLOCK, &set, NULL);
  name_attach_t *a = qd_attach("busgate");
  int bus_up = 0;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    if (!bus_up) { siginfo_t info; sigwaitinfo(&set, &info); bus_up = 1; }
    int frame = m.app.v ^ 0x55;
    MsgReply(rcvid, EOK, &frame, sizeof frame);
  }
}
