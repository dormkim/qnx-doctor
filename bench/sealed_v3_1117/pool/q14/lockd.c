#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* lockd: one shared tool, one holder at a time. A request for a held tool is answered when the holder
 * releases it. v = 1 acquire, v = 0 release. */
int main(void) {
  name_attach_t *a = qd_attach("lockd");
  int busy = 0, waiter = 0;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    if (m.app.v == 1) {
      if (!busy) { busy = 1; MsgReply(rcvid, EOK, NULL, 0); }
      else waiter = rcvid;
    } else {
      MsgReply(rcvid, EOK, NULL, 0);
      if (waiter) { int w = waiter; waiter = 0; MsgReply(w, EOK, NULL, 0); }
      else busy = 0;
    }
  }
}
