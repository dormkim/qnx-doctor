/* auth <me> <keys>: token checker; signs each token with the key service. The key service is opened on
 * first use so auth can start before it. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  int keys = -1;
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    if (keys == -1) keys = qd_open(argv[2]);
    int sig = qd_send(keys, m.app.v);
    MsgReply(rcvid, EOK, &sig, sizeof sig);
    qd_tick(me, n++);
  }
}
