/* nav <me> <gpsd>: navigation loop, one fix per round. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 25);
  int coid = qd_open(argv[2]);
  for (int n = 0;; n++) {
    if (qd_send(coid, n) < 0) { perror("fix"); usleep(100000); continue; }
    qd_tick(me, n);
  }
}
