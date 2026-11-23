/* audiod <me>: mixer control. Only application messages are handled here; anything else on the channel
 * belongs to the resource-manager side and is dropped. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  qd_msg_t m;
  int gain = 0;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    if (m.type != QD_MSG) continue;                 /* not ours */
    gain = m.app.v;
    MsgReply(rcvid, EOK, &gain, sizeof gain);
    qd_tick(me, n++);
  }
}
