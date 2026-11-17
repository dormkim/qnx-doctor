#include "../common/qd.h"
#include <time.h>
#include <signal.h>
#define LATE_PULSE (_PULSE_CODE_MINAVAIL + 3)
int main(void) {   /* answers each request only on the next timer pulse: a slow server, not a lost reply */
  name_attach_t *a = qd_attach("lplate");
  int self = ConnectAttach(0, 0, a->chid, _NTO_SIDE_CHANNEL, 0);
  struct sigevent ev; SIGEV_PULSE_INIT(&ev, self, SIGEV_PULSE_PRIO_INHERIT, LATE_PULSE, 0);
  timer_t tm; timer_create(CLOCK_MONOTONIC, &ev, &tm);
  struct itimerspec it = {{0, 200000000}, {0, 200000000}};
  timer_settime(tm, 0, &it, NULL);
  int held = 0, served = 0;
  for (;;) {
    qd_msg_t m;
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid > 0) { held = rcvid; continue; }
    if (rcvid == 0 && m.pulse.code == LATE_PULSE && held) { served++; MsgReply(held, EOK, &served, sizeof served); held = 0; }
  }
}
