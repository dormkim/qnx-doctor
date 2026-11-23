/* rated <me>: rate-limited request handler. Sheds requests above MAX_INFLIGHT so a burst cannot pile up
 * work; a shed caller simply retries on its next cycle. */
#include "../common/qd.h"

#define MAX_INFLIGHT 6
static int inflight;

static int handle(int v) { return v * 2 + 1; }   /* placeholder for the real conversion */

int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    inflight++;
    if (inflight > MAX_INFLIGHT) continue;           /* shed */
    int r = handle(m.app.v);
    if (r < 0) { inflight--; MsgError(rcvid, EINVAL); continue; }
    MsgReply(rcvid, EOK, &r, sizeof r);
    qd_tick(me, n++);
  }
}
