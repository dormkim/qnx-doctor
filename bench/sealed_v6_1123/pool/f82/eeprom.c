/* eeprom <me>: EEPROM access server, priority 4, fixed-priority channel. ~20 ms per page read. */
#include <time.h>
#include "../common/qd.h"
static void page_ms(int ms) {
  struct timespec a, b; clock_gettime(CLOCK_MONOTONIC, &a);
  do clock_gettime(CLOCK_MONOTONIC, &b);
  while ((b.tv_sec - a.tv_sec) * 1000 + (b.tv_nsec - a.tv_nsec) / 1000000 < ms);
}
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 4);
  int chid = qd_fixed_chan(me);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(chid, &m);
    if (rcvid == 0) continue;
    page_ms(20);
    int word = m.app.v ^ 0xA5;
    qd_tick(me, n++);
    MsgReply(rcvid, EOK, &word, sizeof word);
  }
}
