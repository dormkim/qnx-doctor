#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* evbus: long-poll event server. A client's request is held until the next event; events come from a
 * periodic 300 ms timer pulse and release every held client. */
#define EV_PULSE (_PULSE_CODE_MINAVAIL + 2)
int main(void) {
  name_attach_t *a = qd_attach("evbus");
  int self = ConnectAttach(0, 0, a->chid, _NTO_SIDE_CHANNEL, 0);
  struct sigevent ev; SIGEV_PULSE_INIT(&ev, self, SIGEV_PULSE_PRIO_INHERIT, EV_PULSE, 0);
  timer_t tm; timer_create(CLOCK_MONOTONIC, &ev, &tm);
  struct itimerspec it; memset(&it, 0, sizeof it);
  it.it_value.tv_nsec = 300000000; it.it_interval.tv_nsec = 300000000;
  timer_settime(tm, 0, &it, NULL);
  int held[32], nh = 0, seq = 0;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) {
      if (m.pulse.code != EV_PULSE) continue;
      seq++;
      for (int i = 0; i < nh; i++) MsgReply(held[i], EOK, &seq, sizeof seq);
      nh = 0;
      continue;
    }
    if (nh < 32) held[nh++] = rcvid;
  }
}
