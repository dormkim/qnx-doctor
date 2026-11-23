/* imud <me>: IMU fusion server, priority 6, fixed-priority channel (deterministic timing). */
#include <time.h>
#include "../common/qd.h"
static void fuse_ms(int ms) {
  struct timespec a, b; clock_gettime(CLOCK_MONOTONIC, &a);
  do clock_gettime(CLOCK_MONOTONIC, &b);
  while ((b.tv_sec - a.tv_sec) * 1000 + (b.tv_nsec - a.tv_nsec) / 1000000 < ms);
}
int main(int argc, char **argv) {
  const char *me = argv[1];
  int chid = qd_fixed_chan(me);
  setprio(0, 6);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(chid, &m);
    if (rcvid == 0) continue;
    fuse_ms(25);
    int att = n * 2;
    qd_tick(me, n++);
    MsgReply(rcvid, EOK, &att, sizeof att);
  }
}
