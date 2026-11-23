/* gpsd <me>: position server. Each request waits for the next receiver fix (~150 ms) and returns it.
 * Runs at a low priority (8): position is not time-critical for anyone but nav. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  setprio(0, 8);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    usleep(150000);                               /* wait for the fix */
    qd_tick(me, n);
    int fix = 1000 + n++;
    MsgReply(rcvid, EOK, &fix, sizeof fix);
  }
}
