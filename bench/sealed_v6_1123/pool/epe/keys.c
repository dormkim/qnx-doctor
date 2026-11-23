/* keys <me> <broker>: key service. After the key rotation (every 6th signature) it re-registers its
 * route with the broker so new clients find the new key id. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  int brk = qd_open(argv[2]);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    int sig = m.app.v ^ 0x5a5a;
    if (n % 6 == 5 && qd_send(brk, -1) < 0) perror("register");   /* rotation */
    MsgReply(rcvid, EOK, &sig, sizeof sig);
    qd_tick(me, n++);
  }
}
