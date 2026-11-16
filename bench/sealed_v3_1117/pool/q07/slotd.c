#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* slotd: hands out transmit slots. A request waits for the next slot boundary, which a timer marks
 * with a pulse; at each boundary every waiting radio is released. */
#define SLOT_PULSE (_PULSE_CODE_MINAVAIL + 1)
int main(void) {
  name_attach_t *a = qd_attach("slotd");
  int self = ConnectAttach(0, 0, a->chid, _NTO_SIDE_CHANNEL, 0);
  struct sigevent ev; SIGEV_PULSE_INIT(&ev, self, SIGEV_PULSE_PRIO_INHERIT, SLOT_PULSE, 0);
  timer_t tm; timer_create(CLOCK_MONOTONIC, &ev, &tm);
  struct itimerspec it; memset(&it, 0, sizeof it);
  it.it_value.tv_nsec = 200000000;                    /* slot length 200 ms */
  timer_settime(tm, 0, &it, NULL);
  int waiting[32], nw = 0, slot = 0;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) {
      if (m.pulse.code != SLOT_PULSE) continue;
      slot++;
      for (int i = 0; i < nw; i++) MsgReply(waiting[i], EOK, &slot, sizeof slot);
      nw = 0;
      continue;
    }
    if (nw < 32) waiting[nw++] = rcvid;
  }
}
