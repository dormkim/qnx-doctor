/* adcd <me>: ADC conversion server. Low priority (5) and a fixed-priority channel: conversions must not
 * be sped up or slowed down by whoever asks. Each conversion is ~30 ms of averaging. */
#include <time.h>
#include "../common/qd.h"
static void avg_ms(int ms) {
  struct timespec a, b; clock_gettime(CLOCK_MONOTONIC, &a);
  do clock_gettime(CLOCK_MONOTONIC, &b);
  while ((b.tv_sec - a.tv_sec) * 1000 + (b.tv_nsec - a.tv_nsec) / 1000000 < ms);
}
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 5);
  int chid = qd_fixed_chan(me);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(chid, &m);
    if (rcvid == 0) continue;
    avg_ms(30);
    int mv = 3300 - n;
    qd_tick(me, n++);
    MsgReply(rcvid, EOK, &mv, sizeof mv);
  }
}
