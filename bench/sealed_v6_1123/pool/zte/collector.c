/* collector <me> <merger>: samples a sensor bank and forwards each batch to its merger.
 * A batch is handed over before the next one is accepted from the previous merger, which keeps at most one
 * batch in flight per hop (bounded memory, see design note in the wiki). */
#include "../common/qd.h"

static int link_to(const char *peer) {          /* peer publishes "pid chid" in /tmp/<peer>.chan */
  char path[64]; snprintf(path, sizeof path, "/tmp/%s.chan", peer);
  for (;;) {
    int pid, chid; FILE *f = fopen(path, "r");
    if (f) {
      int got = fscanf(f, "%d %d", &pid, &chid); fclose(f);
      if (got == 2) { int c = ConnectAttach(0, pid, chid, _NTO_SIDE_CHANNEL, 0); if (c != -1) return c; }
    }
    usleep(50000);
  }
}
static int announce(const char *me) {
  int chid = ChannelCreate(0);
  char path[64]; snprintf(path, sizeof path, "/tmp/%s.chan", me);
  FILE *f = fopen(path, "w"); if (chid == -1 || !f) { perror("announce"); exit(1); }
  fprintf(f, "%d %d\n", getpid(), chid); fclose(f);
  return chid;
}

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  const char *me = argv[1];
  int chid = announce(me);
  int batch = 0;
  for (; batch < 3; batch++) { usleep(150000); qd_tick(me, batch); }   /* local sampling until the bank settles */
  int out = link_to(argv[2]);
  qd_msg_t in;
  for (;; batch++) {
    if (qd_send(out, batch) < 0) perror("forward");
    int rcvid = qd_receive(chid, &in);              /* now accept the next batch from upstream */
    if (rcvid > 0) MsgReply(rcvid, EOK, &batch, sizeof batch);
    qd_tick(me, batch);
  }
}
