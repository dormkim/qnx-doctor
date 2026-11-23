/* planner <me> <lidar>: path planner, one scan per planning step. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  int coid = qd_open(argv[2]);
  for (int n = 0;; n++) {
    if (qd_send(coid, n) < 0) perror("scan");
    qd_tick(me, n);
  }
}
