/* pwrmgr <me>: power manager. Requests carry a rail setpoint (>= 0); a negative value is a keep-alive. */
#include <time.h>
#include "../common/qd.h"

#define KEEPALIVE (-1)
static struct timespec last_keepalive;

int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  qd_msg_t m;
  int rail = 0;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    int reply = 1;
    switch (m.app.v) {
    case KEEPALIVE:
      clock_gettime(CLOCK_MONOTONIC, &last_keepalive);
      reply = 0;                                   /* nothing to report back */
      break;
    default:
      rail = m.app.v;
      break;
    }
    if (reply) { MsgReply(rcvid, EOK, &rail, sizeof rail); qd_tick(me, n++); }
  }
}
