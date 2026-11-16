#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* valve: applies an opening level. From level 3 up it first tells pumpctl to slow down,
 * synchronously, so the pump has slowed before the valve opens further. */
int main(void) {
  name_attach_t *a = qd_attach("valve");
  int pump = -1;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    if (m.app.v >= 3) {
      if (pump == -1) pump = qd_open("pumpctl");
      qd_send(pump, -m.app.v);
    }
    MsgReply(rcvid, EOK, NULL, 0);
  }
}
