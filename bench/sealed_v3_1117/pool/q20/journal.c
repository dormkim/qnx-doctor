#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* journal: writes one line per flush; each line carries framestore's frame count. */
int main(void) {
  name_attach_t *a = qd_attach("journal");
  int st = -1;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    if (st == -1) st = qd_open("framestore");
    int count = qd_send(st, -1);                       /* read the store's stats for the line */
    fprintf(stderr, "journal: flush at %d (store has %d)\n", m.app.v, count);
    MsgReply(rcvid, EOK, NULL, 0);
  }
}
