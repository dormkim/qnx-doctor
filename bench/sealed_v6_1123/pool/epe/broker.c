/* broker <me> <auth>: message broker. Client requests go to auth; services may also call in to
 * (re)register their routes. Single-threaded on purpose: route table updates need no locking. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  int auth = qd_open(argv[2]);
  qd_msg_t m;
  int routes = 0;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    int r;
    if (m.app.v < 0) { routes++; r = routes; }    /* route registration */
    else r = qd_send(auth, m.app.v);
    MsgReply(rcvid, EOK, &r, sizeof r);
    qd_tick(me, n++);
  }
}
