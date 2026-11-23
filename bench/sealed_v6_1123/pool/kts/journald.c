/* journald <app role> <io role>: the app thread hands each entry to the io thread over a private channel
 * and waits until io has fsync'ed it (write-through journal). */
#include "../common/qd.h"

static int chid;
static const char *r_io;

static void *io(void *x) {
  FILE *f = NULL;
  pthread_setname_np(pthread_self(), r_io);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(chid, &m);
    if (rcvid <= 0) continue;
    usleep(100000);                               /* fsync on the slow partition */
    if (!f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", r_io); f = fopen(p, "a"); }
    if (f) { fprintf(f, "TICK %s %d\n", r_io, n++); fflush(f); }
    MsgReply(rcvid, EOK, &n, sizeof n);
  }
  return x;
}

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  const char *me = argv[1]; r_io = argv[2];
  chid = ChannelCreate(0);
  if (chid == -1) { perror("ChannelCreate"); return 1; }
  int coid = ConnectAttach(0, 0, chid, _NTO_SIDE_CHANNEL, 0);   /* to ourselves */
  pthread_t t; pthread_create(&t, NULL, io, NULL);
  for (int n = 0;; n++) {
    if (qd_send(coid, n) < 0) perror("journal");
    qd_tick(me, n);
  }
}
