/* merger <me> <next collector>: folds two sample streams and passes the merged block on.
 * Flushes its partial block downstream before taking more input, so a slow consumer cannot make it grow. */
#include "../common/qd.h"

static int chan_of(const char *peer) {
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

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  const char *me = argv[1];
  int chid = ChannelCreate(0);
  char path[64]; snprintf(path, sizeof path, "/tmp/%s.chan", me);
  FILE *f = fopen(path, "w"); if (chid == -1 || !f) { perror("merger"); exit(1); }
  fprintf(f, "%d %d\n", getpid(), chid); fclose(f);

  int blk = 0;
  for (; blk < 2; blk++) { usleep(200000); qd_tick(me, blk); }   /* rebuild the merge table */
  int next = chan_of(argv[2]);
  qd_msg_t m;
  for (;; blk++) {
    qd_send(next, blk);                        /* flush partial block first */
    int rcvid = qd_receive(chid, &m);
    if (rcvid > 0) MsgReply(rcvid, EOK, &blk, sizeof blk);
    qd_tick(me, blk);
  }
}
