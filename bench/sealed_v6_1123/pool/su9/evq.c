/* evq <me>: event queue. A poll request is held until an event is available; events are produced by the
 * 300 ms sampling pulse. */
#include <time.h>
#include "../common/qd.h"
#define SAMPLE (_PULSE_CODE_MINAVAIL + 2)
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  int self = ConnectAttach(0, 0, a->chid, _NTO_SIDE_CHANNEL, 0);
  struct sigevent ev; SIGEV_PULSE_INIT(&ev, self, SIGEV_PULSE_PRIO_INHERIT, SAMPLE, 0);
  timer_t tid; timer_create(CLOCK_MONOTONIC, &ev, &tid);
  struct itimerspec its = { { 0, 300000000 }, { 0, 300000000 } };
  timer_settime(tid, 0, &its, NULL);
  int held = 0, n = 0;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid > 0) { held = rcvid; continue; }    /* park the poll */
    if (m.pulse.code != SAMPLE || !held) continue;
    int e = n;
    qd_tick(me, n++);
    MsgReply(held, EOK, &e, sizeof e);
    held = 0;
  }
}
