/* hmi <me> <sensd>: dashboard refresh. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 28);
  int coid = qd_open(argv[2]);
  for (int n = 0;; n++) {
    int v = qd_send(coid, n * 3);
    if (v < 0) perror("sensd");
    qd_tick(me, n);
  }
}
