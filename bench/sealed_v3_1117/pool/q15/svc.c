#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* svc <me> <peer>: answers a client only after confirming one fact with its peer server.
 * Questions from the peer (negative values) are answered straight away. */
int main(int argc, char **argv) {
  if (argc < 3) return 2;
  name_attach_t *a = qd_attach(argv[1]);
  int peer = -1;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    int v = m.app.v;
    if (v < 0) { int ans = -v; MsgReply(rcvid, EOK, &ans, sizeof ans); continue; }
    usleep(2000);                                   /* local lookup */
    if (peer == -1) peer = qd_open(argv[2]);
    int ok = qd_send(peer, -(v + 1));               /* confirm with the other server */
    MsgReply(rcvid, EOK, &ok, sizeof ok);
  }
}
