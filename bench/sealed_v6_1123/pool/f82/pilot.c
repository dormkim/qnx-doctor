/* pilot <me> <bus>: reads the trim table, priority 35. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 35);
  int bus = qd_open(argv[2]);
  for (int n = 0;; n++) {
    if (qd_send(bus, n & 63) < 0) perror("trim");
    qd_tick(me, n);
    usleep(100000);
  }
}
