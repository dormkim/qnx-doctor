#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* cfgd: configuration store. Key 6 is reserved and rejected. */
static const int table[7] = {10, 20, 30, 40, 50, 60, 0};
int main(void) {
  name_attach_t *a = qd_attach("cfgd");
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    int key = m.app.v % 7;
    if (key == 6) { fprintf(stderr, "cfgd: key %d is reserved, rejecting\n", key); continue; }
    int val = table[key];
    MsgReply(rcvid, EOK, &val, sizeof val);
  }
}
