#include "../common/qd.h"
int main(void) {
  name_attach_t *a = qd_attach("spstore");
  for (;;) { qd_msg_t m; int rcvid = qd_receive(a->chid, &m); if (rcvid > 0) MsgReply(rcvid, EOK, &m.app.v, sizeof m.app.v); }
}
