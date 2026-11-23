/* hmi <me> <gw>: dashboard. Asks the gateway for one record per cycle; between cycles it answers
 * "who owns this key" queries from the database (20 ms window). Its endpoint is in /tmp/<me>.ep. */
#include <time.h>
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  int chid = ChannelCreate(0);
  if (chid == -1) { perror("ChannelCreate"); return 1; }
  char p[64]; snprintf(p, sizeof p, "/tmp/%s.ep", me);
  FILE *f = fopen(p, "w"); if (!f) { perror("ep"); return 1; }
  fprintf(f, "%d %d\n", getpid(), chid); fclose(f);
  int gw = qd_open(argv[2]);
  qd_msg_t m;
  for (int n = 0;; n++) {
    if (qd_send(gw, n) < 0) perror("record");
    qd_tick(me, n);
    for (;;) {                                    /* owner queries */
      uint64_t to = 20000000;
      TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, NULL, &to, NULL);
      rcvid_t r = MsgReceive(chid, &m, sizeof m, NULL);
      if (r == -1) break;
      if (r > 0) { int owner = 1; MsgReply(r, EOK, &owner, sizeof owner); }
    }
    usleep(80000);
  }
}
