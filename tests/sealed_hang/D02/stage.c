/* stage <me> <next>: pass work to the next stage, then accept work from the previous one. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  int next = qd_open(argv[2]);
  qd_msg_t m;
  for (int n = 0;; n++) {
    qd_send(next, n);                 /* QD-CULPRIT: each stage waits for the next one to answer before it ever receives */
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid > 0) MsgReply(rcvid, EOK, &n, sizeof n);
    qd_tick(me, n);
  }
}
