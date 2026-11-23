/* jobd <me> <worker role> <worker role>: job server with two workers.
 * A commit request is confirmed with the submitting client before it is acknowledged (two-phase commit,
 * light). The client puts its notification chid in bits 16..30 of the request. */
#include "../common/qd.h"

#define COMMIT 0x1000
static name_attach_t *att;

static void *worker(void *arg) {
  const char *role = arg; FILE *f = NULL; qd_msg_t m;
  pthread_setname_np(pthread_self(), role);
  for (int n = 0;;) {
    int rcvid = qd_receive(att->chid, &m);
    if (rcvid == 0) continue;
    int v = m.app.v;
    if (v & COMMIT) {
      struct _msg_info info;
      if (MsgInfo(rcvid, &info) != -1) {
        int c = ConnectAttach(0, info.pid, (v >> 16) & 0x7fff, _NTO_SIDE_CHANNEL, 0);
        if (c != -1) { qd_send(c, v & 0xfff); ConnectDetach(c); }   /* phase 2: client confirms */
      }
    }
    MsgReply(rcvid, EOK, &v, sizeof v);
    if (!f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", role); f = fopen(p, "a"); }
    if (f) { fprintf(f, "TICK %s %d\n", role, n++); fflush(f); }
  }
  return NULL;
}

int main(int argc, char **argv) {
  if (argc < 4) return 2;
  att = qd_attach(argv[1]);
  pthread_t a, b;
  pthread_create(&a, NULL, worker, argv[2]);
  pthread_create(&b, NULL, worker, argv[3]);
  pthread_join(a, NULL); pthread_join(b, NULL);
  return 0;
}
