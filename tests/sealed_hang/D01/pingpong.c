/* pingpong <me> <peer> <starts:0|1>: hand a token back and forth. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1], *peer = argv[2];
  name_attach_t *a = qd_attach(me);
  int coid = qd_open(peer);
  qd_msg_t m;
  for (int n = 0;; n++) {
    qd_send(coid, n);                 /* QD-CULPRIT: synchronous send to a peer that is itself sending to us */
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid > 0) MsgReply(rcvid, EOK, &n, sizeof n);
    qd_tick(me, n);
  }
}
