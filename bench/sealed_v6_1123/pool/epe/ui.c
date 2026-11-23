/* ui <me> <broker>: login screen, one token check per cycle. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  int brk = qd_open(argv[2]);
  for (int n = 0;; n++) {
    if (qd_send(brk, n) < 0) perror("check");
    qd_tick(me, n);
    usleep(100000);
  }
}
