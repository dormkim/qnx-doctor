/* player <me> <audiod>: pushes the stream gain each period; at track 5 it also sets the master volume. */
#include "../common/qd.h"
#define QD_VOLUME (QD_MSG + 1)
int main(int argc, char **argv) {
  const char *me = argv[1];
  int coid = qd_open(argv[2]);
  for (int n = 0;; n++) {
    if (n == 5) {
      struct { uint16_t type; int32_t v; } vol = { QD_VOLUME, 70 };
      int r = 0;
      if (MsgSend(coid, &vol, sizeof vol, &r, sizeof r) == -1) perror("volume");
    } else {
      qd_send(coid, n & 31);
    }
    qd_tick(me, n);
    usleep(100000);
  }
}
