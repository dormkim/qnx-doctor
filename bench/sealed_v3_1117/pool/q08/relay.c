#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* relay <me> <next> <origin:0|1>: one stage of a store-and-forward ring.
 * The origin injects an item and waits for it to come back round. Every other stage
 * acknowledges its upstream only after the next stage has taken the item, so an item
 * is never lost when a stage dies half-way. */
int main(int argc, char **argv) {
  if (argc < 4) return 2;
  const char *me = argv[1], *next = argv[2];
  int origin = atoi(argv[3]), down = -1;
  name_attach_t *a = qd_attach(me);
  qd_msg_t m;
  for (int n = 0;; n++) {
    if (origin) {
      if (down == -1) down = qd_open(next);
      qd_send(down, n);                    /* inject; returns once the next stage holds it */
    }
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) { n--; continue; }
    if (!origin) {
      if (down == -1) down = qd_open(next);
      qd_send(down, m.app.v + 1);          /* hand on first ... */
    }
    MsgReply(rcvid, EOK, NULL, 0);         /* ... then acknowledge upstream */
    qd_tick(me, n);
  }
}
