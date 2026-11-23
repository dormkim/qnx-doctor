/* jobc <me> <jobd>: submits a job step every cycle; step 6 is the commit. Between steps it drains its
 * notification channel (20 ms) so jobd never waits on us. */
#include <time.h>
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  int chid = ChannelCreate(0);
  if (chid == -1) { perror("ChannelCreate"); return 1; }
  int coid = qd_open(argv[2]);
  qd_msg_t m;
  for (int n = 0;; n++) {
    int v = (chid << 16) | (n & 0xfff) | (n == 6 ? 0x1000 : 0);
    if (qd_send(coid, v) < 0) perror("submit");
    qd_tick(me, n);
    for (;;) {                                    /* drain notifications */
      uint64_t to = 20000000;
      TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, NULL, &to, NULL);
      rcvid_t r = MsgReceive(chid, &m, sizeof m, NULL);
      if (r == -1) break;
      if (r > 0) MsgReply(r, EOK, NULL, 0);
    }
    usleep(80000);
  }
}
