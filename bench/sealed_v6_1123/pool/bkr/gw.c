/* gw <me> <dbd>: gateway; forwards each record request to the database and passes the answer back. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  int db = qd_open(argv[2]);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    int r = qd_send(db, m.app.v);
    MsgReply(rcvid, EOK, &r, sizeof r);
    qd_tick(me, n++);
  }
}
