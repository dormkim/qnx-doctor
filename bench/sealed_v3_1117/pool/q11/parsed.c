#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* parsed: frame parser. Payloads are 16-bit words, so the length is consumed two bytes at a time. */
int main(void) {
  name_attach_t *a = qd_attach("parsed");
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    volatile int len = m.app.v, words = 0;
    while (len != 0) { len -= 2; words++; }
    int w = words;
    MsgReply(rcvid, EOK, &w, sizeof w);
  }
}
