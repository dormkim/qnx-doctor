/* sensd <me>: sensor hub. A request returns the filtered value after one acquisition window. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  setprio(0, 12);
  qd_msg_t m;
  int filt = 0;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    usleep(120000);                               /* acquisition window */
    filt = (filt * 7 + m.app.v) / 8;
    qd_tick(me, n++);
    MsgReply(rcvid, EOK, &filt, sizeof filt);
  }
}
