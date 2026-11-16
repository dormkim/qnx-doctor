#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* fltr: filters a sample; tells the sampler early (pulse) that the sample arrived, then replies. */
int main(void) {
  name_attach_t *a = qd_attach("fltr");
  int s = -1;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    if (s == -1) s = qd_open("sampler");
    MsgSendPulse(s, -1, _PULSE_CODE_MINAVAIL, m.app.v);   /* early ack */
    int out = m.app.v / 2;
    MsgReply(rcvid, EOK, &out, sizeof out);
  }
}
